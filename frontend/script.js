let currentMood = null;
let filteredTracks = [];

// Redirect the user to Spotify login
function login() {
  window.location.href = 'http://127.0.0.1:8000/login';
}

document.addEventListener('DOMContentLoaded', checkLoginStatus);

function checkLoginStatus() {
  fetch('http://127.0.0.1:8000/me')
    .then(res => {
      if (!res.ok) throw new Error('Not logged in');
      return res.json();
    })
    .then(data => {
      const loginBtn = document.getElementById('login-btn');
      const greeting = document.getElementById('user-greeting');
      loginBtn.style.display = 'none';
      greeting.textContent = `Hi, ${data.display_name}`;
      greeting.style.display = 'inline';
    })
    .catch(() => {
      // Not logged in – show login button
    });
}


// Fetch and render all liked tracks (unfiltered)
function showAllLiked() {
  fetch('http://127.0.0.1:8000/all-liked-tracks')
    .then(res => res.json())
    .then(data => {
      const list = document.getElementById('track-list');
      list.innerHTML = '';

      if (!Array.isArray(data) || data.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'You have no liked tracks.';
        list.appendChild(li);
        return;
      }

      data.forEach(track => {
        const li = document.createElement('li');
        li.textContent = `${track.name} — ${track.artist}`;
        list.appendChild(li);
      });
    })
    .catch(err => {
      console.error('Failed to fetch liked tracks:', err);
    });
}

// Called when a mood button is clicked
function selectMood(mood) {
  currentMood = mood;
  fetch(`http://127.0.0.1:8000/mood-tracks?mood=${mood}`)
    .then(res => res.json())
    .then(data => {
      // Update the track list in the UI and store URIs
      updateTrackList(data);
    })
    .catch(err => {
      console.error('Error fetching mood tracks:', err);
    });
}

// Render the list of tracks and save their URIs for playlist creation
function updateTrackList(tracks) {
  const listEl = document.getElementById('track-list');
  listEl.innerHTML = '';
  filteredTracks = tracks;

  if (!tracks.length) {
    const li = document.createElement('li');
    li.textContent = 'No matching tracks found.';
    listEl.appendChild(li);
    return;
  }

  tracks.forEach(track => {
    const li = document.createElement('li');
    li.textContent = `${track.name} — ${track.artist}`;
    listEl.appendChild(li);
  });
}

// Called when the "Create Playlist" button is clicked
function createPlaylist() {
  if (!currentMood || !filteredTracks.length) {
    alert('Please select a mood and wait for matching tracks.');
    return;
  }

  const uris = filteredTracks.map(t => t.uri);
  fetch('http://127.0.0.1:8000/create-playlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mood: currentMood, uris })
  })
  .then(res => res.json())
  .then(data => {
    if (data.playlist_url) {
      window.open(data.playlist_url, '_blank');
    } else {
      alert('Error: ' + (data.error || 'Unknown error'));
    }
  });
}


