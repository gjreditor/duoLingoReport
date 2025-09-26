import os
import requests
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from PIL import Image
import numpy as np

# -------------------------
# CONFIG
# -------------------------
DUO_USERNAME = os.getenv("DUO_USERNAME")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://www.duolingo.com/2017-06-30"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/139.0.0.0 Safari/537.36"
}

# -------------------------
# FUNCTIONS
# -------------------------
def get_user_data(username):
    url = f"{BASE_URL}/users?username={username}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        raise ValueError(f"HTTP Error {resp.status_code}")
    data = resp.json()
    return data["users"][0]

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"  # allows *bold* and formatting
    }
    resp = requests.post(url, data=payload)
    if resp.status_code != 200:
        print(f"Error sending message: {resp.text}")

def send_user_summary(bot_token, chat_id, user):
    streak = user.get("streak", 0)
    total_xp = sum(c.get("xp", 0) for c in user.get("courses", []))
    
    # Sort top 3 courses by XP
    courses = sorted(user.get("courses", []), key=lambda c: c.get("xp", 0), reverse=True)[:3]
    course_lines = [f"- {c['title']}: {c['xp']} XP" for c in courses]

    message = (
        f"📊 *Duolingo Dashboard for {user['username']}*\n\n"
        f"🔥 Streak: *{streak} days*\n"
        f"⭐ Total XP: *{total_xp}*\n\n"
        f"🏆 Top Courses:\n" + "\n".join(course_lines)
    )

    send_telegram_message(bot_token, chat_id, message)

def generate_dashboard_gif(user, filename="duo_dashboard.gif"):
    streak_length = user.get("streak", 0)
    courses = user.get("courses", [])
    course_names = [c['title'] for c in courses]
    course_xp = [c['xp'] for c in courses]
    
    frames = []
    tmp_files = []
    target_size = None  # reference frame size

    # Animate streak progression (always at least one frame)
    max_days = max(streak_length, 7)
    if streak_length == 0:
        # Show an empty bar with "0 days"
        fig, ax = plt.subplots(figsize=(5,2))
        ax.barh([0], [0], color='green')
        ax.set_xlim(0, max_days)
        ax.set_yticks([])
        ax.set_title(f"{user['username']}'s streak animation")
        ax.set_xlabel("Days (0)")
        plt.tight_layout()
        
        tmp_file = "frame_streak_0.png"
        tmp_files.append(tmp_file)
        plt.savefig(tmp_file)
        plt.close(fig)

        img = Image.open(tmp_file).convert("RGB")
        target_size = img.size
        frames.append(np.array(img))
    else:
        for i in range(1, min(streak_length, 7)+1):
            fig, ax = plt.subplots(figsize=(5,2))
            ax.barh([0], [i], color='green')
            ax.set_xlim(0, max_days)
            ax.set_yticks([])
            ax.set_title(f"{user['username']}'s streak animation")
            ax.set_xlabel("Days")
            plt.tight_layout()
            
            tmp_file = f"frame_streak_{i}.png"
            tmp_files.append(tmp_file)
            plt.savefig(tmp_file)
            plt.close(fig)

            img = Image.open(tmp_file).convert("RGB")
            if target_size is None:
                target_size = img.size
            else:
                img = img.resize(target_size)
            frames.append(np.array(img))

    # Animate XP per course
    max_xp = max(course_xp) if course_xp else 1
    for j in range(1, 11):  # 10 animation frames
        fig, ax = plt.subplots(figsize=(6,3))
        animated_xp = [xp * j/10 for xp in course_xp]
        ax.bar(course_names, animated_xp, color='skyblue')
        ax.set_ylim(0, max_xp*1.1)
        ax.set_ylabel("XP")
        ax.set_title(f"{user['username']}'s XP progress")
        plt.tight_layout()
        
        tmp_file = f"frame_xp_{j}.png"
        tmp_files.append(tmp_file)
        plt.savefig(tmp_file)
        plt.close(fig)

        img = Image.open(tmp_file).convert("RGB")
        img = img.resize(target_size)
        frames.append(np.array(img))

    # Save all frames as GIF
    imageio.mimsave(filename, frames, duration=0.8)

    # Cleanup temporary PNG files
    for f in tmp_files:
        if os.path.exists(f):
            os.remove(f)

    return filename

def send_telegram_animation(bot_token, chat_id, gif_file):
    url = f"https://api.telegram.org/bot{bot_token}/sendAnimation"
    with open(gif_file, "rb") as f:
        files = {"animation": f}
        payload = {"chat_id": chat_id}
        requests.post(url, data=payload, files=files)
    print(f"Sent animated dashboard to chat {chat_id}")

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    if not all([DUO_USERNAME, BOT_TOKEN, CHAT_ID]):
        raise ValueError("Set DUO_USERNAME, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID environment variables")
    
    user = get_user_data(DUO_USERNAME)
    send_user_summary(BOT_TOKEN, CHAT_ID, user)
    gif_file = generate_dashboard_gif(user)
    send_telegram_animation(BOT_TOKEN, CHAT_ID, gif_file)

