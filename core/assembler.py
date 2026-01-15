import os
import whisper
import moviepy.video.fx as vfx
from moviepy import AudioFileClip, TextClip, CompositeVideoClip, ImageClip
from moviepy.audio.AudioClip import CompositeAudioClip
from core.db_manager import DBManager

# NOTE: Ensure this path is correct for your system.
# If deploying to Linux, you will need to change this to a Linux font path (e.g., /usr/share/fonts/...)
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
BGM_PATH = r"data/music/background.mp3"


class VideoAssembler:
    def __init__(self):
        self.db = DBManager()
        self.output_dir = "data/final_videos"
        os.makedirs(self.output_dir, exist_ok=True)
        self.model = whisper.load_model("base")

    def assemble(self):
        task = self.db.collection.find_one({"status": "ready_to_assemble"})
        if not task:
            print("📭 No tasks ready.")
            return

        print(f"🎬 Assembly with Ken Burns: {task['title']}")

        audio = AudioFileClip(task["audio_path"])
        total_duration = audio.duration

        print("🎙️ Analyzing audio timing...")
        result = self.model.transcribe(task["audio_path"], word_timestamps=True)
        segments = result["segments"]

        visual_scenes = task.get("visual_scenes", [])
        if not visual_scenes:
            return

        timeline_clips = []
        caption_clips = []

        for i, segment in enumerate(segments):
            start_time = segment["start"]
            end_time = (
                segments[i + 1]["start"] if i < len(segments) - 1 else total_duration
            )
            block_duration = end_time - start_time
            if block_duration <= 0:
                continue

            scene_index = i % len(visual_scenes)
            path = visual_scenes[scene_index]["path"]

            try:
                # 1. Create Image Clip
                img_clip = ImageClip(path).with_duration(block_duration)

                # 2. Apply Dynamic Zoom (Ken Burns)
                # We crop a slightly smaller window and move it, or just zoom in center
                # Simple Center Zoom Logic for MoviePy:
                img_clip = img_clip.resized(height=1920)
                if img_clip.w > 1080:
                    img_clip = img_clip.cropped(x_center=img_clip.w / 2, width=1080)

                # The Trick: Resize from 1.0 to 1.15 over time
                img_clip = img_clip.with_effects([vfx.Resize(lambda t: 1 + 0.05 * t)])

                # Re-crop to ensure it stays 1080x1920 after zooming
                img_clip = img_clip.cropped(
                    x_center=img_clip.w / 2,
                    y_center=img_clip.h / 2,
                    width=1080,
                    height=1920,
                )

                img_clip = img_clip.with_start(start_time)
                timeline_clips.append(img_clip)

            except Exception as e:
                print(f"⚠️ Clip error: {e}")

            # Captions
            for word in segment["words"]:
                w_start = word["start"]
                w_end = max(word["end"], w_start + 0.1)
                safe_text = f" {word['word'].strip().upper()} "

                caption = (
                    TextClip(
                        text=safe_text,
                        font=FONT_PATH,
                        font_size=75,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=4,
                        margin=(20, 20),
                    )
                    .with_start(w_start)
                    .with_duration(w_end - w_start)
                    # UPDATED POSITION:
                    # "center" horizontally.
                    # 1600 vertically (Total height is 1920, so 1600 is near the bottom).
                    .with_position(("center", 1600))
                )
                caption_clips.append(caption)

        if not timeline_clips:
            return

        bg_video = CompositeVideoClip(timeline_clips, size=(1080, 1920)).with_duration(
            total_duration
        )

        if os.path.exists(BGM_PATH):
            bgm = (
                AudioFileClip(BGM_PATH)
                .with_duration(total_duration)
                .multiply_volume(0.12)
            )
            final_audio = CompositeAudioClip([audio, bgm])
        else:
            final_audio = audio

        final_video = CompositeVideoClip([bg_video] + caption_clips).with_audio(
            final_audio
        )

        out_path = os.path.join(self.output_dir, f"FINAL_{task['_id']}.mp4")
        print("📦 Rendering...")

        try:
            final_video.write_videofile(
                out_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                threads=4,
                preset="fast",
            )
            self.db.collection.update_one(
                {"_id": task["_id"]},
                {"$set": {"status": "completed", "final_video_path": out_path}},
            )
            print(f"🎉 DONE: {out_path}")
        except Exception as e:
            print(f"❌ Render Failed: {e}")
        finally:
            try:
                final_video.close()
                audio.close()
            except:
                pass
