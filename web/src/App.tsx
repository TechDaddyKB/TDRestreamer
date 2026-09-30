import {
  FormEvent,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  api,
  APIError,
  Principal,
  Session,
  Resource,
  Capabilities,
} from "./api";
const APIDocs = lazy(() => import("./Docs"));
const pages = [
  "Overview",
  "Sessions",
  "OBS inputs",
  "Destinations",
  "Compatibility",
  "API documentation",
] as const;
type Page = (typeof pages)[number];
const mark = ["◉", "▤", "⇥", "↗", "◇", "⌘"];
export function App() {
  const [user, setUser] = useState<Principal | null>(null),
    [checking, setChecking] = useState(true),
    [page, setPage] = useState<Page>("Overview");
  const [error, setError] = useState(""),
    [theme, setTheme] = useState(
      () => localStorage.getItem("tdr-theme") ?? "dark",
    );
  const [sessions, setSessions] = useState<Session[]>([]),
    [inputs, setInputs] = useState<Resource[]>([]),
    [destinations, setDestinations] = useState<Resource[]>([]),
    [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const refresh = useCallback(async () => {
    try {
      const [ss, ii, dd, cc] = await Promise.all([
        api<{ items: Session[] }>("/sessions"),
        api<{ items: Resource[] }>("/inputs"),
        api<{ items: Resource[] }>("/destinations"),
        api<Capabilities>("/capabilities"),
      ]);
      setSessions(ss.items);
      setInputs(ii.items);
      setDestinations(dd.items);
      setCapabilities(cc);
    } catch (e) {
      setError(message(e));
      if (e instanceof APIError && e.status === 401) setUser(null);
    }
  }, []);
  const identify = useCallback(async () => {
    try {
      setUser(await api<Principal>("/auth/me"));
    } catch (e) {
      if (!(e instanceof APIError && e.status === 401)) setError(message(e));
    } finally {
      setChecking(false);
    }
  }, []);
  useEffect(() => {
    void identify();
  }, [identify]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("tdr-theme", theme);
  }, [theme]);
  useEffect(() => {
    if (!user) return;
    void refresh();
    const events = new EventSource("/api/v1/events");
    const update = () => void refresh();
    for (const kind of ["session.test", "session.prepare", "session.stop"])
      events.addEventListener(kind, update);
    return () => events.close();
  }, [user, refresh]);
  if (checking)
    return (
      <main className="login">
        <p role="status">Connecting to your appliance…</p>
      </main>
    );
  if (!user) return <Auth onLogin={identify} initialError={error} />;
  const operate = ["admin", "streamer", "operator"].includes(user.role),
    edit =
      ["admin", "streamer"].includes(user.role) ||
      (user.role === "operator" && user.edit_granted),
    secrets = ["admin", "streamer"].includes(user.role);
  async function logout() {
    try {
      await api("/auth/logout", {});
      setUser(null);
      setError("");
    } catch (e) {
      setError(message(e));
    }
  }
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="#main">
          <span className="logo">TD</span>
          <span>
            TECH DADDY’S<strong>Restreamer</strong>
          </span>
        </a>
        <p className="nav-caption">YOUR WORKSPACE</p>
        <nav aria-label="Main navigation">
          {pages.map((p, i) => (
            <button
              key={p}
              aria-current={page === p ? "page" : undefined}
              onClick={() => {
                setPage(p);
                setError("");
              }}
            >
              <span aria-hidden="true">{mark[i]}</span>
              {p}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="badge">DEVELOPMENT</span>
          <p>
            Local control plane
            <br />
            <small>Media qualification in progress</small>
          </p>
          <a href="https://github.com/camarokris/TDRestreamer">
            Source & documentation ↗
          </a>
        </div>
      </aside>
      <div className="workspace">
        <header>
          <span>
            Workspace / <b>{page}</b>
          </span>
          <div className="header-controls">
            <label className="sr-only" htmlFor="theme">
              Color theme
            </label>
            <select
              id="theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="contrast">High contrast</option>
            </select>
            <span className="role">{user.role}</span>
            <button className="subtle" onClick={() => void logout()}>
              Sign out
            </button>
          </div>
        </header>
        <main id="main">
          <div className="page-title">
            <div>
              <p className="eyebrow">ONE FEED. MORE POSSIBILITIES.</p>
              <h1>{page === "Overview" ? "Your streaming workspace" : page}</h1>
              <p className="muted">
                {page === "Overview"
                  ? "Prepare your inputs and destinations, with a clear view of what’s ready."
                  : "Configure with confidence. Changes are saved to your appliance."}
              </p>
            </div>
            <span className="connection">● Control connected</span>
          </div>
          <div className="notice">
            <b>Development preview</b>
            <span>
              Configuration and compatibility planning work here. Media ingest,
              live publishing, browser preview, platform login and cloud workers
              are not available yet.
            </span>
          </div>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          {page === "Overview" && (
            <>
              <div className="stats">
                {[
                  ["Sessions", sessions.length, "Saved configurations"],
                  ["OBS inputs", inputs.length, "Tokens protected"],
                  [
                    "Destinations",
                    destinations.length,
                    "Credentials encrypted",
                  ],
                  [
                    "Publishing",
                    capabilities?.publishing ? "Available" : "Not ready",
                    "Qualification required",
                  ],
                ].map(([label, value, note]) => (
                  <section className="stat" key={label}>
                    <p>{label}</p>
                    <strong>{value}</strong>
                    <small>{note}</small>
                  </section>
                ))}
              </div>
              <div className="overview-grid">
                <section className="card">
                  <p className="eyebrow">GET STREAM-READY</p>
                  <h2>A deliberate path to going live</h2>
                  <p className="muted">
                    Save your setup now. Live output stays unavailable until the
                    media pipeline passes its acceptance checks.
                  </p>
                  <ol className="steps">
                    {[
                      [
                        "01",
                        "Add your OBS inputs",
                        "Create distinct horizontal, vertical or combined-canvas input identities.",
                        "OBS inputs",
                      ],
                      [
                        "02",
                        "Choose destinations",
                        "Store output credentials without exposing them again.",
                        "Destinations",
                      ],
                      [
                        "03",
                        "Review compatibility",
                        "Check geometry, supplied audio tracks and conversion needs.",
                        "Compatibility",
                      ],
                    ].map(([n, title, desc, target]) => (
                      <li key={n}>
                        <span className="step-number">{n}</span>
                        <div>
                          <h3>{title}</h3>
                          <p>{desc}</p>
                        </div>
                        <button
                          className="subtle"
                          onClick={() => setPage(target as Page)}
                          aria-label={title}
                        >
                          →
                        </button>
                      </li>
                    ))}
                  </ol>
                </section>
                <section className="card accent">
                  <span className="badge">SAFE BY DEFAULT</span>
                  <h2>
                    Prepare first.
                    <br />
                    Publish deliberately.
                  </h2>
                  <p>
                    Test mode never sends media to your streaming destinations
                    or starts a platform broadcast.
                  </p>
                  <hr />
                  <h3>Your current boundaries</h3>
                  <ul>
                    <li>Manual Go Live is the default.</li>
                    <li>Software encoding requires approval.</li>
                    <li>Saved stream keys stay write-only.</li>
                    <li>No recording, replay or DVR.</li>
                  </ul>
                </section>
              </div>
            </>
          )}
          {page === "Sessions" && (
            <Sessions
              items={sessions}
              operate={operate}
              onChange={refresh}
              onError={setError}
            />
          )}
          {page === "OBS inputs" && (
            <ResourcePage
              kind="inputs"
              items={inputs}
              editable={edit}
              onChange={refresh}
              onError={setError}
            />
          )}
          {page === "Destinations" && (
            <ResourcePage
              kind="destinations"
              items={destinations}
              editable={secrets}
              onChange={refresh}
              onError={setError}
            />
          )}
          {page === "Compatibility" && <Compatibility onError={setError} />}
          {page === "API documentation" && (
            <section className="card docs">
              <Suspense fallback={<p>Loading API documentation…</p>}>
                <APIDocs />
              </Suspense>
            </section>
          )}
          <footer>
            Tech Daddy’s Restreamer{" "}
            <span>AGPL-3.0-or-later · Development build</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
function message(e: unknown) {
  return e instanceof Error
    ? e.message
    : "The operation could not be completed";
}
function Auth({
  onLogin,
  initialError,
}: {
  onLogin: () => Promise<void>;
  initialError: string;
}) {
  const [setup, setSetup] = useState(false),
    [error, setError] = useState(initialError),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setError("");
    setBusy(true);
    try {
      if (setup) {
        await api("/auth/bootstrap", {
          username: data.get("username"),
          password: data.get("password"),
          bootstrap_token: data.get("token"),
          tenant_name: data.get("tenant"),
        });
        setSetup(false);
        setNotice("Workspace created. Sign in with your new account.");
        form.reset();
      } else {
        await api("/auth/login", {
          username: data.get("username"),
          password: data.get("password"),
        });
        await onLogin();
      }
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <section className="login-story">
        <span className="logo">TD</span>
        <p className="eyebrow">TECH DADDY’S RESTREAMER</p>
        <h1>
          Your stream.
          <br />
          Your appliance.
        </h1>
        <p>A workspace for preparing, testing and managing your broadcasts.</p>
        <span className="badge">DEVELOPMENT PREVIEW</span>
        <p className="muted">
          This build manages configuration. Live media and external integrations
          are still being qualified.
        </p>
      </section>
      <section className="card login-form">
        <h2>{setup ? "Set up your appliance" : "Welcome back"}</h2>
        <p className="muted">
          {setup
            ? "Use the one-time setup credential generated on your host."
            : "Sign in to your local workspace."}
        </p>
        <form onSubmit={submit}>
          <label>
            Username
            <input
              name="username"
              autoComplete="username"
              required
              maxLength={120}
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={setup ? "new-password" : "current-password"}
              required
              minLength={setup ? 12 : 1}
              maxLength={1024}
            />
          </label>
          {setup && (
            <>
              <label>
                Workspace name
                <input name="tenant" required maxLength={120} />
              </label>
              <label>
                One-time setup credential
                <input
                  name="token"
                  type="password"
                  autoComplete="off"
                  required
                />
              </label>
            </>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          {notice && <p role="status">{notice}</p>}
          <button className="primary" disabled={busy}>
            {busy ? "Working…" : setup ? "Create workspace" : "Sign in"}
          </button>
        </form>
        <button
          className="subtle"
          onClick={() => {
            setSetup(!setup);
            setError("");
          }}
        >
          {setup
            ? "Already configured? Sign in"
            : "First time? Set up this appliance"}
        </button>
        <p className="fine">
          Discord and Google login are not implemented in this development
          build.
        </p>
      </section>
    </main>
  );
}
function Sessions({
  items,
  operate,
  onChange,
  onError,
}: {
  items: Session[];
  operate: boolean;
  onChange: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    try {
      await api("/sessions", { name: new FormData(form).get("name") });
      form.reset();
      await onChange();
    } catch (e) {
      onError(message(e));
    } finally {
      setBusy(false);
    }
  }
  async function action(item: Session, action: string) {
    setBusy(true);
    try {
      await api(
        "/sessions/" + item.id + "/" + action,
        { revision: item.revision },
        { "Idempotency-Key": crypto.randomUUID() },
      );
      await onChange();
    } catch (e) {
      onError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card">
      <h2>Session configurations</h2>
      <p className="muted">
        Test and prepare update desired state only. No media is processed in
        this build.
      </p>
      {operate && (
        <form className="inline-form" onSubmit={create}>
          <label>
            Session name
            <input
              name="name"
              required
              maxLength={120}
              placeholder="Friday evening stream"
            />
          </label>
          <button className="primary" disabled={busy}>
            Create session
          </button>
        </form>
      )}
      {items.length === 0 ? (
        <Empty
          title="No sessions yet"
          text="Create a named session to organize your streaming setup."
        />
      ) : (
        <div className="resource-list">
          {items.map((i) => (
            <article className="resource" key={i.id}>
              <div>
                <h3>{i.name}</h3>
                <p>
                  Desired state: <b>{i.state}</b> · Revision {i.revision}
                </p>
              </div>
              {operate && (
                <div className="actions">
                  <button
                    disabled={
                      busy ||
                      !["idle", "ended", "failed", "armed"].includes(i.state)
                    }
                    onClick={() => void action(i, "test")}
                  >
                    Set test mode
                  </button>
                  <button
                    disabled={busy || ["idle", "ended"].includes(i.state)}
                    onClick={() => void action(i, "stop")}
                  >
                    Stop
                  </button>
                  <button disabled title="Media publishing is not implemented">
                    Go Live unavailable
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
function ResourcePage({
  kind,
  items,
  editable,
  onChange,
  onError,
}: {
  kind: "inputs" | "destinations";
  items: Resource[];
  editable: boolean;
  onChange: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [token, setToken] = useState(""),
    [busy, setBusy] = useState(false);
  const input = kind === "inputs";
  useEffect(() => {
    setToken("");
  }, [kind]);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      d = new FormData(form);
    setBusy(true);
    setToken("");
    try {
      const res = await api<{ token?: string }>(
        "/" + kind,
        input
          ? { name: d.get("name"), orientation: d.get("orientation") }
          : {
              name: d.get("name"),
              platform: d.get("platform"),
              url: d.get("url"),
            },
      );
      if (res.token) setToken(res.token);
      form.reset();
      await onChange();
    } catch (e) {
      onError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="overview-grid">
      <section className="card">
        <h2>{input ? "Your OBS input identities" : "Your destinations"}</h2>
        <p className="muted">
          {input
            ? "Separate feeds have separate identities. Ingest listeners are not active yet."
            : "Stored URLs and stream keys are encrypted and never returned."}
        </p>
        {items.length === 0 ? (
          <Empty
            title={
              input ? "No inputs configured" : "No destinations configured"
            }
            text="Use the adjacent form to save your first configuration."
          />
        ) : (
          <div className="resource-list">
            {items.map((i) => (
              <article className="resource" key={i.id}>
                <div>
                  <h3>{i.name}</h3>
                  <p>{i.orientation ?? i.platform} · Credential saved</p>
                </div>
                <span className="badge">CONFIGURED</span>
              </article>
            ))}
          </div>
        )}
      </section>
      {editable && (
        <section className="card">
          <h2>Add {input ? "input" : "destination"}</h2>
          <form onSubmit={submit}>
            <label>
              Name
              <input name="name" required maxLength={120} />
            </label>
            {input ? (
              <label>
                Input orientation
                <select name="orientation">
                  <option value="horizontal">Horizontal</option>
                  <option value="vertical">Vertical</option>
                  <option value="master">Combined canvas</option>
                </select>
              </label>
            ) : (
              <>
                <label>
                  Platform
                  <select name="platform">
                    {[
                      "generic",
                      "youtube",
                      "twitch",
                      "kick",
                      "x",
                      "rumble",
                    ].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Full RTMP / RTMPS URL
                  <input
                    name="url"
                    type="password"
                    autoComplete="off"
                    required
                    maxLength={4096}
                  />
                </label>
                <p className="fine">
                  Include your stream key in the URL. Platform delivery and
                  OAuth are not yet available.
                </p>
              </>
            )}
            <button className="primary" disabled={busy}>
              {busy ? "Saving…" : "Save " + (input ? "input" : "destination")}
            </button>
          </form>
          {token && (
            <div className="one-time" role="status">
              <b>Save this token now</b>
              <p>It will never be shown again after leaving this view.</p>
              <code>{token}</code>
              <button onClick={() => setToken("")}>
                I have saved it — dismiss
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
function Compatibility({ onError }: { onError: (s: string) => void }) {
  const [result, setResult] = useState<{
      results: { category: string; reason: string }[];
    } | null>(null),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const d = new FormData(e.currentTarget),
      vertical = d.get("orientation") === "vertical";
    setBusy(true);
    setResult(null);
    try {
      setResult(
        await api("/compatibility/evaluate", {
          rule_revision: "generic-v1",
          input: {
            width: Number(d.get("width")),
            height: Number(d.get("height")),
            fps: 30,
            video_codec: "h264",
            audio_codec: "aac",
            audio_tracks: [0],
            verified: true,
          },
          targets: [
            {
              id: "proposal",
              input_id: "manual-example",
              width: vertical ? 1080 : 1920,
              height: vertical ? 1920 : 1080,
              fps: 30,
              bitrate_kbps: 6000,
              video_codec: "h264",
              audio_codec: "aac",
              audio_track: 0,
              transform: vertical ? "crop" : "none",
              allow_transcode: d.get("approve") === "on",
            },
          ],
        }),
      );
    } catch (e) {
      onError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card planner">
      <h2>Explore a profile</h2>
      <p className="muted">
        This is a manual geometry/codec proposal, not validation of a live input
        or a platform’s bitrate/GOP rules. The example assumes H.264/AAC at 30
        fps with audio track 0.
      </p>
      <form onSubmit={submit}>
        <div className="field-grid">
          <label>
            Input width
            <input
              name="width"
              type="number"
              defaultValue={1920}
              min={2}
              max={8192}
              step={2}
              required
            />
          </label>
          <label>
            Input height
            <input
              name="height"
              type="number"
              defaultValue={1080}
              min={2}
              max={8192}
              step={2}
              required
            />
          </label>
          <label>
            Output orientation
            <select name="orientation">
              <option value="horizontal">Horizontal · 1920 × 1080</option>
              <option value="vertical">Vertical · 1080 × 1920</option>
            </select>
          </label>
        </div>
        <label className="checkbox">
          <input name="approve" type="checkbox" />
          Approve video conversion for this proposal
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Evaluating…" : "Evaluate compatibility"}
        </button>
      </form>
      {result && (
        <div className="result" role="status">
          <span className="badge">PROPOSAL</span>
          <h3>{result.results[0].category.replaceAll("_", " ")}</h3>
          <p>{result.results[0].reason}</p>
        </div>
      )}
    </section>
  );
}
function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <span aria-hidden="true">◇</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
