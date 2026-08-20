// Front end for the /report API.
//
// The flow mirrors the server's job pattern exactly:
//   1. POST the two files to /report        -> get back a job_id (202 Accepted)
//   2. Poll GET /report/{job_id} every 2s   -> until status is "done" or "failed"
//   3. Render the finished markdown report
//
// Step 2 is the interesting part: the server does the slow work in the
// background, so the browser has to keep ASKING "is it done yet?" (pulling),
// because the server can't push a result to us over a plain HTTP request.
//
// Every request is authenticated: we attach a Clerk session token as an
// "Authorization: Bearer <token>" header, and the backend verifies it.

// Grab the page elements once, up front.
const form = document.getElementById("report-form");
const myArmyInput = document.getElementById("my-army");
const enemyArmyInput = document.getElementById("enemy-army");
const submitButton = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const reportEl = document.getElementById("report");
const printButton = document.getElementById("print-btn");
const authLoadingEl = document.getElementById("auth-loading");
const signInEl = document.getElementById("sign-in");
const userButtonEl = document.getElementById("user-button");

// How often to re-check the job, in milliseconds.
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 60;

// A tiny helper to pause for a while inside an async function.
// (There's no built-in "sleep" in JavaScript, so we wrap setTimeout in a Promise.)
function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

// Show a message in the status line. `isError` flips it red.
function showStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

// ---------------------------------------------------------------------------
// AUTH (Clerk) — sign the visitor in and hand out session tokens.
// ---------------------------------------------------------------------------

// The publishable key is public, but we still read it from OUR backend so the
// value lives in .env, not hardcoded in this file.
async function loadPublishableKey() {
  const response = await fetch("/config");
  const config = await response.json();
  return config.clerk_publishable_key;
}

// ClerkJS is served from your own Clerk instance's domain, and that domain is
// encoded inside the publishable key — so we decode it instead of hardcoding.
// A key looks like:  pk_test_<base64 of "your-domain.clerk.accounts.dev$">
function frontendApiFromKey(publishableKey) {
  const encodedDomain = publishableKey.split("_")[2];
  return atob(encodedDomain).replace(/\$$/, ""); // drop the trailing "$"
}

// Add the ClerkJS <script> to the page and wait for it to finish loading.
function loadClerkScript(publishableKey) {
  const frontendApi = frontendApiFromKey(publishableKey);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://${frontendApi}/npm/@clerk/clerk-js@5/dist/clerk.browser.js`;
    script.async = true;
    script.crossOrigin = "anonymous";
    script.setAttribute("data-clerk-publishable-key", publishableKey);
    script.addEventListener("load", resolve);
    script.addEventListener("error", () => reject(new Error("Failed to load ClerkJS")));
    document.head.appendChild(script);
  });
}

// Show the right UI for whether the visitor is signed in or not. Called once at
// startup and again whenever Clerk tells us the auth state changed.
let signInMounted = false;
function renderAuthState() {
  authLoadingEl.hidden = true;
  const signedIn = Boolean(Clerk.user);

  form.hidden = !signedIn;
  signInEl.hidden = signedIn;

  if (signedIn) {
    Clerk.mountUserButton(userButtonEl);
  } else if (!signInMounted) {
    // Mount the sign-in widget once; Clerk keeps it in sync after that.
    Clerk.mountSignIn(signInEl);
    signInMounted = true;
  }
}

// The Authorization header for an API call, with a FRESH token each time.
// Clerk tokens are short-lived; getToken() refreshes them automatically, so we
// ask for one right before every request (including each poll).
async function authHeaders() {
  const token = await Clerk.session.getToken();
  return { Authorization: `Bearer ${token}` };
}

async function initAuth() {
  const publishableKey = await loadPublishableKey();
  await loadClerkScript(publishableKey);
  await Clerk.load();

  renderAuthState();
  Clerk.addListener(renderAuthState); // re-render on sign in / sign out
}

// ---------------------------------------------------------------------------
// THE REPORT FLOW
// ---------------------------------------------------------------------------

// STEP 1 — send the two files, get a job_id back.
async function submitReport(myArmyFile, enemyArmyFile) {
  // FormData is how the browser builds a multipart/form-data upload. The field
  // names ("my_army", "enemy_army") must match what the endpoint expects.
  const formData = new FormData();
  formData.append("my_army", myArmyFile);
  formData.append("enemy_army", enemyArmyFile);

  const response = await fetch("/report", {
    method: "POST",
    body: formData,
    headers: await authHeaders(),
  });

  if (!response.ok) {
    // The API sends {"detail": "..."} on a 400/401/422; surface that if it's there.
    const problem = await response.json().catch(() => null);
    const detail = problem?.detail ?? `Request failed (${response.status})`;
    throw new Error(detail);
  }

  const body = await response.json();
  return body.job_id;
}

// STEP 2 — keep asking the server until the job is finished.
async function pollUntilFinished(jobId) {
  var poll_count = 0;
  while (true) {
    const response = await fetch(`/report/${jobId}`, {
      headers: await authHeaders(),
    });
    const job = await response.json();
    

    if (job.status === "DONE") {
      return job.result;
    }
    if (job.status === "ERROR") {
      throw new Error(job.error_msg ?? "The report failed to generate.");
    }

    // Still "pending" — wait, then loop around and ask again.
    await sleep(POLL_INTERVAL_MS);
    poll_count++;
    if (poll_count >= MAX_POLL_COUNT) {
      throw new Error("Report generation timed out.");
    }
  }
}

// STEP 3 — render the markdown report as HTML.
function renderReport(markdown) {
  reportEl.innerHTML = marked.parse(markdown);
  printButton.hidden = false; // reveal "Print report" now that there's something to print
}

// Wire the whole flow to the form's submit.
form.addEventListener("submit", async (event) => {
  event.preventDefault(); // stop the browser's default page reload

  // Lock the button and clear any previous run.
  submitButton.disabled = true;
  reportEl.innerHTML = "";
  printButton.hidden = true;

  try {
    showStatus("Submitting…");
    const jobId = await submitReport(myArmyInput.files[0], enemyArmyInput.files[0]);

    showStatus("Generating report… this can take a bit.");
    const report = await pollUntilFinished(jobId);

    showStatus("Done.");
    renderReport(report);
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});

// The print button just opens the browser's print dialog; the @media print
// rules in index.html strip the page down to the report itself. (The dialog's
// "Save as PDF" option means this doubles as a PDF export.)
printButton.addEventListener("click", () => window.print());

// Kick everything off: get auth ready before the user can do anything.
initAuth().catch((error) => {
  authLoadingEl.hidden = true;
  showStatus(`Could not start sign-in: ${error.message}`, true);
});
