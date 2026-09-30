# Hardware qualification matrix

No device family is certified yet. N100/8GB/1GbE is the minimum target, not a claim
that it can perform five arbitrary transcodes. Reference platforms remain Linux
x86-64 CPU, Intel QSV/VAAPI, NVIDIA NVDEC/NVENC, AMD VAAPI and ARM64 CPU.

For every qualification record capture OS/kernel, driver, FFmpeg build flags, codecs,
filter graph, device IDs, workload, resource use, audio/video timing, failure behavior
and actual test duration. An encoder appearing in `ffmpeg -encoders` is not proof.

Required baseline: five 1080p30 H.264/AAC relay sessions, three controlled outputs
each, for eight hours on N100. Separate eight-hour single-session H/V transform
soaks on each GPU family and measured higher capacity. Exercise dual input, combined
canvas, crop/fill/blur and multi-device assignment independently. Qualification
includes physical capacity admission rather than an arbitrary five-session quota.
