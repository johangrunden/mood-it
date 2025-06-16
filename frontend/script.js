
function login() {
    window.location.href = 'http://127.0.0.1:8000/login';
}

function selectMood(mood) {
    fetch(`http://127.0.0.1:8000/mood-tracks?mood=${mood}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("track-list");
            list.innerHTML = "";

            if (!Array.isArray(data) || data.length === 0) {
                const li = document.createElement("li");
                li.textContent = "No matching tracks found.";
                list.appendChild(li);
                return;
            }

            data.forEach(track => {
                const li = document.createElement("li");
                li.textContent = `${track.name} – ${track.artist}`;
                list.appendChild(li);
            });
        })
        .catch(err => {
            console.error("Fetch failed:", err);
        });
}

function showAllLiked() {
    fetch("http://127.0.0.1:8000/all-liked-tracks")
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("track-list");
            list.innerHTML = "";

            if (!Array.isArray(data) || data.length === 0) {
                const li = document.createElement("li");
                li.textContent = "You have no liked songs.";
                list.appendChild(li);
                return;
            }

            data.forEach(track => {
                const li = document.createElement("li");
                li.textContent = `${track.name} – ${track.artist}`;
                list.appendChild(li);
            });
        })
        .catch(err => {
            console.error("Fetch failed:", err);
        });
}


function createPlaylist() {
    alert("Playlist creation not implemented yet.");
}
