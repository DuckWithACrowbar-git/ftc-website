function checkPassword() {
  const password = document.getElementById("passwordInput").value;

  // ⚠️ Hardcoding password is insecure, but okay for demo
  const correctPassword = "test";

  if (password === correctPassword) {
    // Redirect to another HTML file
    window.location.href = "s1rfxuj9yk.html";
  } else {
    alert("Incorrect password. Try again.");
  }
}
