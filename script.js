// script.js - example for the login form 
document.querySelector("#loginForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const pw = document.querySelector("#password").value;
  const form = new URLSearchParams();
  form.append("password", pw);

  const res = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString()
  });

  // server redirects on success; follow will auto-handle, but we can check:
  if (res.redirected) {
    window.location = res.url;
  } else {
    // fallback - try to go to /media/
    window.location = "/media/";
  }
});

