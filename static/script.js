document.addEventListener("DOMContentLoaded", function() {
    const loginForm = document.querySelector("form[action='/signin']");
    const signupForm = document.querySelector("form[action='/signup']");

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = loginForm.email.value;
            const password = loginForm.password.value;

            const res = await fetch("https://hiimzia.pythonanywhere.com/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json();
            if (data.success) {
                alert(`Welcome ${data.name}`);
                window.location.href = "/dummy"; // or a frontend page
            } else {
                alert(data.message);
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = signupForm.name.value;
            const email = signupForm.email.value;
            const password = signupForm.password.value;

            const res = await fetch("https://hiimzia.pythonanywhere.com/api/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password })
            });

            const data = await res.json();
            if (data.success) {
                alert("Signup successful!");
                window.location.href = "/"; // redirect to login
            } else {
                alert(data.message);
            }
        });
    }
});
