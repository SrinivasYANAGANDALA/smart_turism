// app/static/js/scripts.js
// PURE JAVASCRIPT — NO HTML — NO JINJA

function triggerPanic() {
    if (!confirm("🚨 EMERGENCY SOS\n\nThis will notify your emergency contact. Continue?")) {
        return;
    }

    const button = document.querySelector(".panic-button");
    if (!button) {
        alert("SOS button not found");
        return;
    }

    const originalHTML = button.innerHTML;
    button.innerHTML = "⏳";
    button.disabled = true;

    fetch("/send-sos", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: "Emergency SOS triggered",
            latitude: null,
            longitude: null
        })
    })
    .then(response => response.json())
    .then(data => {
        button.innerHTML = originalHTML;
        button.disabled = false;

        if (data.success) {
            alert("✅ SOS SENT!\nEmergency contact notified.");
        } else {
            alert("❌ SOS FAILED");
        }
    })
    .catch(error => {
        console.error(error);
        button.innerHTML = originalHTML;
        button.disabled = false;
        alert("❌ Network error while sending SOS");
    });
}
