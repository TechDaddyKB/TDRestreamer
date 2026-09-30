/* Bounded M0 RTSP -> enhanced-RTMP copy publisher.
 * The playpath arrives on stdin; never put ingest authentication in argv.
 */
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libavcodec/codec_par.h>
#include <libavformat/avformat.h>
#include <libavutil/error.h>
#include <libavutil/time.h>

#define FLV_FILTER_CAPACITY (4 * 1024 * 1024)

typedef struct FlvFilter {
    AVIOContext *target;
    uint8_t *pending;
    size_t used;
    int header_sent;
    unsigned enhanced_primary_tags;
} FlvFilter;

static int emit_bytes(FlvFilter *filter, const uint8_t *data, size_t size)
{
    avio_write(filter->target, data, size);
    avio_flush(filter->target);
    return filter->target->error < 0 ? filter->target->error : 0;
}

static int emit_flv_tag(FlvFilter *filter, const uint8_t *tag, size_t total)
{
    const uint8_t *payload = tag + 11;
    size_t size = ((size_t)tag[1] << 16) | ((size_t)tag[2] << 8) | tag[3];
    if (tag[0] != 9 || size < 5 || (payload[0] & 0x8f) != 7 ||
        payload[1] > 2)
        return emit_bytes(filter, tag, total);

    uint8_t header[11];
    memcpy(header, tag, sizeof(header));
    uint8_t first = 0x80 | (payload[0] & 0x70) | payload[1];
    uint8_t fourcc[5] = {first, 'a', 'v', 'c', '1'};
    int code;
    if (payload[1] == 1) {
        size_t new_size = size + 3;
        if (new_size > 0xffffff)
            return AVERROR_INVALIDDATA;
        header[1] = (new_size >> 16) & 0xff;
        header[2] = (new_size >> 8) & 0xff;
        header[3] = new_size & 0xff;
        uint8_t previous[4] = {(new_size + 11) >> 24,
                               (new_size + 11) >> 16,
                               (new_size + 11) >> 8, new_size + 11};
        if ((code = emit_bytes(filter, header, sizeof(header))) < 0 ||
            (code = emit_bytes(filter, fourcc, sizeof(fourcc))) < 0 ||
            (code = emit_bytes(filter, payload + 2, size - 2)) < 0 ||
            (code = emit_bytes(filter, previous, sizeof(previous))) < 0)
            return code;
    } else {
        if ((code = emit_bytes(filter, header, sizeof(header))) < 0 ||
            (code = emit_bytes(filter, fourcc, sizeof(fourcc))) < 0 ||
            (code = emit_bytes(filter, payload + 5, size - 5)) < 0 ||
            (code = emit_bytes(filter, tag + 11 + size, 4)) < 0)
            return code;
    }
    ++filter->enhanced_primary_tags;
    return 0;
}

static int filter_write(void *opaque, const uint8_t *data, int size)
{
    FlvFilter *filter = opaque;
    if (size < 0 || filter->used + (size_t)size > FLV_FILTER_CAPACITY)
        return AVERROR_INVALIDDATA;
    memcpy(filter->pending + filter->used, data, size);
    filter->used += size;
    while (filter->used >= (filter->header_sent ? 15 : 13)) {
        size_t total;
        if (!filter->header_sent) {
            if (memcmp(filter->pending, "FLV", 3) != 0)
                return AVERROR_INVALIDDATA;
            total = 13;
        } else {
            size_t payload = ((size_t)filter->pending[1] << 16) |
                             ((size_t)filter->pending[2] << 8) |
                             filter->pending[3];
            total = 11 + payload + 4;
            if (total > FLV_FILTER_CAPACITY)
                return AVERROR_INVALIDDATA;
            if (filter->used < total)
                break;
        }
        int code = filter->header_sent ?
            emit_flv_tag(filter, filter->pending, total) :
            emit_bytes(filter, filter->pending, total);
        if (code < 0)
            return code;
        filter->header_sent = 1;
        filter->used -= total;
        memmove(filter->pending, filter->pending + total, filter->used);
    }
    return size;
}

static volatile sig_atomic_t stopping;
static int64_t deadline_us;

static void stop_signal(int unused)
{
    (void)unused;
    stopping = 1;
}

static int interrupted(void *unused)
{
    (void)unused;
    return stopping || av_gettime_relative() >= deadline_us;
}

static int report_error(const char *stage, int code)
{
    char message[AV_ERROR_MAX_STRING_SIZE];
    av_strerror(code, message, sizeof(message));
    fprintf(stderr, "%s: %s\n", stage, message);
    return 1;
}

static int write_rebased(AVFormatContext *input, AVFormatContext *output,
                         AVPacket *packet, const int64_t base_us[6],
                         int64_t first_output_key_ms[4])
{
    unsigned index = (unsigned)packet->stream_index;
    AVRational source_time_base = input->streams[index]->time_base;
    int64_t offset = av_rescale_q(base_us[index] - 2000000,
                                  AV_TIME_BASE_Q, source_time_base);
    packet->pts -= offset;
    packet->dts -= offset;
    av_packet_rescale_ts(packet, source_time_base, output->streams[index]->time_base);
    if (index < 4 && (packet->flags & AV_PKT_FLAG_KEY) &&
        first_output_key_ms[index] == AV_NOPTS_VALUE)
        first_output_key_ms[index] = av_rescale_q(
            packet->pts, output->streams[index]->time_base, (AVRational){1, 1000});
    return av_interleaved_write_frame(output, packet);
}

static int valid_source(const char *url)
{
    const char *local = "rtsp://127.0.0.1:18555/dual/";
    const char *bridged = "rtsp://127.0.0.1:18556/dual/";
    return (strncmp(url, local, strlen(local)) == 0 && url[strlen(local)] != '\0') ||
           (strncmp(url, bridged, strlen(bridged)) == 0 && url[strlen(bridged)] != '\0');
}

static int valid_destination(const char *url)
{
    return strcmp(url, "rtmp://127.0.0.1:19351/dual") == 0 ||
           strcmp(url, "rtmps://ingest.global-contribute.live-video.net/app") == 0;
}

static int contains_bytes(const uint8_t *data, size_t size,
                          const uint8_t *needle, size_t needle_size)
{
    if (size < needle_size)
        return 0;
    for (size_t offset = 0; offset <= size - needle_size; ++offset) {
        if (memcmp(data + offset, needle, needle_size) == 0)
            return 1;
    }
    return 0;
}

static int copy_media(const char *source, const char *destination,
                      const char *app, const char *playpath, int seconds)
{
    AVFormatContext *input = NULL;
    AVFormatContext *output = NULL;
    AVIOContext *remote_io = NULL;
    AVIOContext *filtered_io = NULL;
    FlvFilter filter = {0};
    AVDictionary *options = NULL;
    AVPacket *packet = NULL;
    unsigned dropped[6] = {0};
    unsigned seen_timestamp[6] = {0};
    unsigned keyframes[4] = {0};
    unsigned bpm_ts[4] = {0};
    unsigned bpm_sm[4] = {0};
    unsigned bpm_erm[4] = {0};
    unsigned dropped_bpm[4] = {0};
    unsigned keyframes_with_bpm[4] = {0};
    unsigned bpm_pending[4][3] = {{0}};
    AVPacket **buffered = NULL;
    size_t buffered_count = 0;
    size_t buffered_bytes = 0;
    int64_t pending_index[4] = {-1, -1, -1, -1};
    int64_t start_index[4] = {-1, -1, -1, -1};
    int64_t first_ready_pts_us[4] = {AV_NOPTS_VALUE, AV_NOPTS_VALUE,
                                     AV_NOPTS_VALUE, AV_NOPTS_VALUE};
    int64_t base_us[6] = {0};
    int64_t first_output_key_ms[4] = {AV_NOPTS_VALUE, AV_NOPTS_VALUE,
                                      AV_NOPTS_VALUE, AV_NOPTS_VALUE};
    int opened = 0;
    int64_t first_key_pts[4] = {AV_NOPTS_VALUE, AV_NOPTS_VALUE,
                                AV_NOPTS_VALUE, AV_NOPTS_VALUE};
    static const uint8_t ts_uuid[16] = {
        0x0a, 0xec, 0xff, 0xe7, 0x52, 0x72, 0x4e, 0x2f,
        0xa6, 0x2f, 0xd1, 0x9c, 0xd6, 0x1a, 0x93, 0xb5};
    static const uint8_t sm_uuid[16] = {
        0xca, 0x60, 0xe7, 0x1c, 0x6a, 0x8b, 0x43, 0x88,
        0xa3, 0x77, 0x15, 0x1d, 0xf7, 0xbf, 0x8a, 0xc2};
    static const uint8_t erm_uuid[16] = {
        0xf1, 0xfb, 0xc1, 0xd5, 0x10, 0x1e, 0x4f, 0xb5,
        0xa6, 0x1e, 0xb8, 0xce, 0x3c, 0x07, 0xb8, 0xc0};
    int result = 1;
    int code;
    int64_t preparation_deadline;

    avformat_network_init();
    deadline_us = av_gettime_relative() + (int64_t)seconds * 1000000;
    preparation_deadline = av_gettime_relative() + 12000000;
    input = avformat_alloc_context();
    if (input == NULL) {
        fprintf(stderr, "input_context: allocation failed\n");
        goto done;
    }
    input->interrupt_callback.callback = interrupted;
    av_dict_set(&options, "rtsp_transport", "tcp", 0);
    code = avformat_open_input(&input, source, NULL, &options);
    av_dict_free(&options);
    if (code < 0) {
        result = report_error("rtsp_open", code);
        goto done;
    }
    input->flags |= AVFMT_FLAG_GENPTS;
    code = avformat_find_stream_info(input, NULL);
    if (code < 0) {
        result = report_error("stream_info", code);
        goto done;
    }
    if (input->nb_streams != 6) {
        fprintf(stderr, "stream_count: expected four video and two audio tracks\n");
        goto done;
    }
    for (unsigned i = 0; i < 6; ++i) {
        enum AVCodecID expected = i < 4 ? AV_CODEC_ID_H264 : AV_CODEC_ID_AAC;
        if (input->streams[i]->codecpar->codec_id != expected) {
            fprintf(stderr, "stream_order: unexpected codec at index %u\n", i);
            goto done;
        }
    }

    code = avformat_alloc_output_context2(&output, NULL, "flv", destination);
    if (code < 0 || output == NULL) {
        result = report_error("output_context", code < 0 ? code : AVERROR(ENOMEM));
        goto done;
    }
    for (unsigned i = 0; i < 6; ++i) {
        AVStream *stream = avformat_new_stream(output, NULL);
        if (stream == NULL) {
            fprintf(stderr, "output_stream: allocation failed\n");
            goto done;
        }
        code = avcodec_parameters_copy(stream->codecpar, input->streams[i]->codecpar);
        if (code < 0) {
            result = report_error("codec_copy", code);
            goto done;
        }
        stream->codecpar->codec_tag = 0;
        stream->time_base = input->streams[i]->time_base;
    }

    output->interrupt_callback.callback = interrupted;
    packet = av_packet_alloc();
    if (packet == NULL) {
        fprintf(stderr, "packet: allocation failed\n");
        goto done;
    }
    buffered = calloc(4096, sizeof(*buffered));
    if (buffered == NULL) {
        fprintf(stderr, "startup_buffer: allocation failed\n");
        goto done;
    }
    while (!interrupted(NULL)) {
        if (!opened && av_gettime_relative() >= preparation_deadline) {
            fprintf(stderr, "startup_gate: aligned BPM keyframes not observed\n");
            goto done;
        }
        code = av_read_frame(input, packet);
        if (code < 0) {
            if (interrupted(NULL))
                break;
            result = report_error("rtsp_read", code);
            goto done;
        }
        unsigned index = (unsigned)packet->stream_index;
        if (index >= 6) {
            fprintf(stderr, "packet_stream: invalid index\n");
            goto done;
        }
        if (packet->pts == AV_NOPTS_VALUE || packet->dts == AV_NOPTS_VALUE) {
            if (index < 4)
                dropped_bpm[index] += contains_bytes(packet->data, packet->size,
                                                       ts_uuid, sizeof(ts_uuid)) ||
                                      contains_bytes(packet->data, packet->size,
                                                     sm_uuid, sizeof(sm_uuid)) ||
                                      contains_bytes(packet->data, packet->size,
                                                     erm_uuid, sizeof(erm_uuid));
            if (seen_timestamp[index] || ++dropped[index] > 120) {
                fprintf(stderr, "timestamp_gap: invalid packet at index %u\n", index);
                goto done;
            }
            av_packet_unref(packet);
            continue;
        }
        seen_timestamp[index] = 1;
        int64_t position = -1;
        if (!opened) {
            if (buffered_count >= 4096 || buffered_bytes + packet->size > 64 * 1024 * 1024) {
                fprintf(stderr, "startup_buffer: limit exceeded\n");
                goto done;
            }
            position = (int64_t)buffered_count;
            buffered[buffered_count] = av_packet_clone(packet);
            if (buffered[buffered_count] == NULL) {
                fprintf(stderr, "startup_buffer: packet allocation failed\n");
                goto done;
            }
            ++buffered_count;
            buffered_bytes += packet->size;
        }
        if (index < 4) {
            unsigned has_ts = contains_bytes(packet->data, packet->size,
                                             ts_uuid, sizeof(ts_uuid));
            unsigned has_sm = contains_bytes(packet->data, packet->size,
                                             sm_uuid, sizeof(sm_uuid));
            unsigned has_erm = contains_bytes(packet->data, packet->size,
                                              erm_uuid, sizeof(erm_uuid));
            bpm_ts[index] += has_ts;
            bpm_sm[index] += has_sm;
            bpm_erm[index] += has_erm;
            bpm_pending[index][0] |= has_ts;
            bpm_pending[index][1] |= has_sm;
            bpm_pending[index][2] |= has_erm;
            if (!opened && pending_index[index] < 0 && (has_ts || has_sm || has_erm))
                pending_index[index] = position;
            if (packet->flags & AV_PKT_FLAG_KEY) {
                int complete_bpm = bpm_pending[index][0] && bpm_pending[index][1] &&
                                   bpm_pending[index][2];
                keyframes_with_bpm[index] += complete_bpm;
                if (opened && !complete_bpm) {
                    fprintf(stderr, "bpm_gap: incomplete markers before keyframe %u\n", index);
                    goto done;
                }
                if (!opened && complete_bpm && start_index[index] < 0) {
                    start_index[index] = pending_index[index];
                    first_ready_pts_us[index] = av_rescale_q(
                        packet->pts, input->streams[index]->time_base, AV_TIME_BASE_Q);
                }
                memset(bpm_pending[index], 0, sizeof(bpm_pending[index]));
                pending_index[index] = -1;
                if (first_key_pts[index] == AV_NOPTS_VALUE)
                    first_key_pts[index] = av_rescale_q(packet->pts,
                                                         input->streams[index]->time_base,
                                                         (AVRational){1, 1000});
                ++keyframes[index];
            }
        }
        if (!opened) {
            if (start_index[0] < 0 || start_index[1] < 0 ||
                start_index[2] < 0 || start_index[3] < 0) {
                av_packet_unref(packet);
                continue;
            }
            int64_t latest_start = first_ready_pts_us[0];
            for (unsigned i = 0; i < 4; ++i) {
                base_us[i] = first_ready_pts_us[i];
                if (first_ready_pts_us[i] > latest_start)
                    latest_start = first_ready_pts_us[i];
            }
            base_us[4] = base_us[5] = latest_start;
            av_dict_set(&options, "rtmp_app", app, 0);
            av_dict_set(&options, "rtmp_playpath", playpath, 0);
            if (strcmp(destination, "rtmps://ingest.global-contribute.live-video.net/app") == 0)
                av_dict_set(&options, "tls_verify", "1", 0);
            /* OBS 32.2.2 does not advertise fourCcList in its RTMP connect packet. */
            code = avio_open2(&remote_io, destination, AVIO_FLAG_WRITE,
                              &output->interrupt_callback, &options);
            av_dict_free(&options);
            if (code < 0) {
                result = report_error("rtmp_open", code);
                goto done;
            }
            filter.target = remote_io;
            filter.pending = malloc(FLV_FILTER_CAPACITY);
            uint8_t *avio_buffer = av_malloc(32768);
            if (filter.pending == NULL || avio_buffer == NULL) {
                av_free(avio_buffer);
                fprintf(stderr, "flv_filter: allocation failed\n");
                goto done;
            }
            filtered_io = avio_alloc_context(avio_buffer, 32768, 1, &filter,
                                             NULL, filter_write, NULL);
            if (filtered_io == NULL) {
                av_free(avio_buffer);
                fprintf(stderr, "flv_filter: context allocation failed\n");
                goto done;
            }
            output->pb = filtered_io;
            output->flags |= AVFMT_FLAG_CUSTOM_IO;
            code = avformat_write_header(output, NULL);
            if (code < 0) {
                result = report_error("flv_header", code);
                goto done;
            }
            opened = 1;
            for (size_t i = 0; i < buffered_count; ++i) {
                AVPacket *held = buffered[i];
                unsigned stream = (unsigned)held->stream_index;
                int include = stream < 4 ? (int64_t)i >= start_index[stream] :
                    av_rescale_q(held->pts, input->streams[stream]->time_base,
                                 AV_TIME_BASE_Q) >= latest_start - 100000;
                if (include) {
                    code = write_rebased(input, output, held, base_us,
                                         first_output_key_ms);
                    if (code < 0) {
                        result = report_error("rtmp_startup_write", code);
                        goto done;
                    }
                }
                av_packet_free(&buffered[i]);
            }
            buffered_count = 0;
            av_packet_unref(packet);
            continue;
        }
        code = write_rebased(input, output, packet, base_us,
                             first_output_key_ms);
        if (code < 0) {
            if (interrupted(NULL))
                break;
            result = report_error("rtmp_write", code);
            goto done;
        }
    }
    if (!opened) {
        fprintf(stderr, "startup_gate: publisher never opened\n");
        goto done;
    }
    code = av_write_trailer(output);
    if (code < 0 && !interrupted(NULL)) {
        result = report_error("flv_trailer", code);
        goto done;
    }
    result = 0;

done:
    fprintf(stderr, "startup_missing_timestamps=%u,%u,%u,%u,%u,%u\n",
            dropped[0], dropped[1], dropped[2], dropped[3], dropped[4], dropped[5]);
    fprintf(stderr, "keyframes=%u,%u,%u,%u\n",
            keyframes[0], keyframes[1], keyframes[2], keyframes[3]);
    fprintf(stderr, "first_key_pts_ms=%lld,%lld,%lld,%lld\n",
            (long long)first_key_pts[0], (long long)first_key_pts[1],
            (long long)first_key_pts[2], (long long)first_key_pts[3]);
    fprintf(stderr, "bpm_ts=%u,%u,%u,%u\n",
            bpm_ts[0], bpm_ts[1], bpm_ts[2], bpm_ts[3]);
    fprintf(stderr, "bpm_sm=%u,%u,%u,%u\n",
            bpm_sm[0], bpm_sm[1], bpm_sm[2], bpm_sm[3]);
    fprintf(stderr, "bpm_erm=%u,%u,%u,%u\n",
            bpm_erm[0], bpm_erm[1], bpm_erm[2], bpm_erm[3]);
    fprintf(stderr, "keyframes_with_bpm=%u,%u,%u,%u\n",
            keyframes_with_bpm[0], keyframes_with_bpm[1],
            keyframes_with_bpm[2], keyframes_with_bpm[3]);
    fprintf(stderr, "dropped_bpm=%u,%u,%u,%u\n",
            dropped_bpm[0], dropped_bpm[1], dropped_bpm[2], dropped_bpm[3]);
    fprintf(stderr, "first_ready_pts_ms=%lld,%lld,%lld,%lld\n",
            (long long)(first_ready_pts_us[0] / 1000),
            (long long)(first_ready_pts_us[1] / 1000),
            (long long)(first_ready_pts_us[2] / 1000),
            (long long)(first_ready_pts_us[3] / 1000));
    fprintf(stderr, "first_output_key_pts_ms=%lld,%lld,%lld,%lld\n",
            (long long)first_output_key_ms[0], (long long)first_output_key_ms[1],
            (long long)first_output_key_ms[2], (long long)first_output_key_ms[3]);
    fprintf(stderr, "enhanced_primary_tags=%u\n", filter.enhanced_primary_tags);
    av_packet_free(&packet);
    for (size_t i = 0; i < buffered_count; ++i)
        av_packet_free(&buffered[i]);
    free(buffered);
    if (filtered_io != NULL) {
        avio_flush(filtered_io);
        avio_context_free(&filtered_io);
    }
    if (output != NULL)
        output->pb = NULL;
    if (remote_io != NULL)
        avio_closep(&remote_io);
    free(filter.pending);
    avformat_free_context(output);
    avformat_close_input(&input);
    av_dict_free(&options);
    avformat_network_deinit();
    return result;
}

int main(int argc, char **argv)
{
    char playpath[1024];
    char *end;
    long seconds;
    if (argc != 4 || !valid_source(argv[1]) || !valid_destination(argv[2])) {
        fprintf(stderr, "usage: twitch_copy <loopback RTSP> <approved RTMP(S)> <seconds>\n");
        return 2;
    }
    seconds = strtol(argv[3], &end, 10);
    if (*argv[3] == '\0' || *end != '\0' || seconds < 1 || seconds > 300) {
        fprintf(stderr, "duration: must be 1..300 seconds\n");
        return 2;
    }
    if (fgets(playpath, sizeof(playpath), stdin) == NULL || strchr(playpath, '\n') == NULL) {
        fprintf(stderr, "playpath: missing or too long\n");
        return 2;
    }
    playpath[strcspn(playpath, "\n")] = '\0';
    if (playpath[0] == '\0' || strchr(playpath, '/') != NULL ||
        strspn(playpath, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-?=&.%")
            != strlen(playpath)) {
        fprintf(stderr, "playpath: invalid\n");
        return 2;
    }
    signal(SIGTERM, stop_signal);
    signal(SIGINT, stop_signal);
    av_log_set_level(strcmp(argv[2], "rtmp://127.0.0.1:19351/dual") == 0 ?
                     AV_LOG_WARNING : AV_LOG_QUIET);
    return copy_media(argv[1], argv[2],
                      strstr(argv[2], "rtmps://") == argv[2] ? "app" : "dual",
                      playpath, (int)seconds);
}
