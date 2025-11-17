function checkPassword() {
  const password = document.getElementById("passwordInput").value.trim();

  // ⚠️ Hardcoding password is insecure, but okay for demo
  const correctPassword = "test";

  // If no password entered, redirect back to index.html
  if (!password) {
    window.location.href = "index.html";
    return;
  }

  if (password === correctPassword) {
    // Mark session as authenticated (client-side only)
    sessionStorage.setItem('authenticated', 'true');
    // Redirect to protected media folder
    window.location.href = "media/";
  } else {
    alert("Incorrect password. Try again.");
  }
}
