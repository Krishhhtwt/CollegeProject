document.addEventListener("DOMContentLoaded", () => {
  const loginBtn = document.getElementById("loginBtn");

  if (loginBtn) {
    loginBtn.addEventListener("click", async () => {
      const user = document.getElementById("userId").value.trim();
      const pass = document.getElementById("password").value.trim();

      if (!user || !pass) {
        showMessage("⚠️ Please fill all fields", "error");
        return;
      }

      
      if (user === "24bcs12159" && pass === "krish@2977") {
        showMessage("✅ Login Successful!", "success");
        localStorage.setItem("loggedIn", "true");
        setTimeout(() => (window.location.href = "dashboard.html"), 800);
      } else {
        showMessage("❌ Invalid User ID or Password!", "error");
      }
    });
  }
});


function submitLeave() {
  const teacherName = document.getElementById("teacherName").value;
  const date = document.getElementById("date").value;
  const reason = document.getElementById("reason").value;

  if (!teacherName || !date || !reason) {
    alert("⚠️ Please fill all fields before submitting leave!");
    return;
  }

  fetch("/api/leave", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ teacher_name: teacherName, date, reason })
  })
    .then(res => res.json())
    .then(data => {
      console.log("Leave Response:", data);
      alert(`✅ ${data.message}\n🧑 Substitute: ${data.substitute_teacher}`);
    })
    .catch(err => {
      console.error("Error submitting leave:", err);
      alert("❌ Failed to submit leave. Please try again!");
    });
}

// TEACHERS 
fetch("/api/teachers")
  .then(res => res.json())
  .then(data => {
    console.log("Teachers:", data);
    const list = document.getElementById("teachers-list");
    if (list) {
      list.innerHTML = data.map(t => `<li>${t.teacher_name} - ${t.subject}</li>`).join("");
    }
  })
  .catch(err => console.error("Error fetching teachers:", err));

//  TIMETABLE 
fetch("/api/timetable")
  .then(res => res.json())
  .then(data => {
    console.log("Timetable:", data);
    const table = document.getElementById("timetable");
    if (table) {
      table.innerHTML = data
        .map(
          t => `
          <tr>
            <td>${t.teacher_name}</td>
            <td>${t.subject}</td>
            <td>${t.day}</td>
            <td>${t.start_time}</td>
            <td>${t.end_time}</td>
            <td>${t.class_name}</td>
          </tr>`
        )
        .join("");
    }
  })
  .catch(err => console.error("Error fetching timetable:", err));

// LOGOUT 
function logout() {
  localStorage.removeItem("loggedIn");
  showMessage(" Logged out successfully!", "success");
  setTimeout(() => (window.location.href = "index.html"), 1000);
}

// MESSAGE BOX 
function showMessage(msg, type = "info") {
  const box = document.getElementById("messageBox");
  if (!box) {
    alert(msg);
    return;
  }
  box.innerHTML = msg;
  box.className = type;
}
