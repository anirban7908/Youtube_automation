import os
import whisper

# 1. Import vfx for effects like Loop
import moviepy.video.fx as vfx
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.audio.AudioClip import CompositeAudioClip
from core.db_manager import DBManager

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
BGM_PATH = r"data/music/background.mp3"


class VideoAssembler:
    def __init__(self):
        self.db = DBManager()
        self.output_dir = "data/final_videos"
        os.makedirs(self.output_dir, exist_ok=True)
        # Use "tiny" or "base" model to save RAM if "Insufficient resources" persists
        self.model = whisper.load_model("base")

    def assemble(self):
        task = self.db.collection.find_one({"status": "ready_to_assemble"})
        if not task:
            print("📭 No tasks ready for assembly.")
            return

        print(f"🎬 Scene-Based Assembly: {task['title']}")

        # Load Audio
        audio = AudioFileClip(task["audio_path"])
        total_duration = audio.duration

        visual_scenes = task.get("visual_scenes", [])
        if not visual_scenes:
            print("❌ No visual scenes found.")
            return

        num_scenes = len(visual_scenes)
        scene_duration = (
            total_duration / num_scenes if num_scenes > 0 else total_duration
        )

        print(f"🧩 {num_scenes} scenes → {scene_duration:.2f}s each")

        timeline_clips = []
        current_time = 0

        # ---------------- SCENE LOOP ----------------
        for scene in visual_scenes:
            clips = scene.get("clips", [])
            if not clips:
                continue

            per_clip_duration = scene_duration / len(clips)

            for clip_data in clips:
                path = clip_data["path"]

                try:
                    # Load video without audio to save processing
                    v = VideoFileClip(path).without_audio()

                    # 2. FIXED LOOP SYNTAX (MoviePy v2)
                    if v.duration < per_clip_duration:
                        # Old: v = v.loop(duration=per_clip_duration)
                        # New: Use vfx.Loop effect
                        v = v.with_effects([vfx.Loop(duration=per_clip_duration)])
                    else:
                        v = v.subclipped(0, per_clip_duration)

                    # Resize to vertical (9:16)
                    v = v.resized(height=1920)
                    if v.w > 1080:
                        v = v.cropped(x_center=v.w / 2, width=1080)

                    # Set timing on the timeline
                    v = v.with_start(current_time).with_duration(per_clip_duration)

                    timeline_clips.append(v)
                    current_time += per_clip_duration

                except Exception as e:
                    print(f"⚠️ Clip error: {path} → {e}")

        if not timeline_clips:
            print("❌ Error: No valid clips were created. Aborting.")
            return

        # ---------------- BACKGROUND VIDEO ----------------
        bg_video = CompositeVideoClip(timeline_clips, size=(1080, 1920)).with_duration(
            total_duration
        )

        # ---------------- CAPTIONS ----------------
        print("📝 Generating word-level captions...")
        result = self.model.transcribe(task["audio_path"], word_timestamps=True)

        caption_clips = []

        for segment in result["segments"]:
            for word in segment["words"]:
                start = word["start"]
                end = max(word["end"], start + 0.1)

                caption = (
                    TextClip(
                        text=word["word"].upper(),
                        font=FONT_PATH,
                        font_size=80,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=4,
                        method="caption",
                        size=(900, None),
                    )
                    .with_start(start)
                    .with_duration(end - start)
                    .with_position(("center", 1400))
                )

                caption_clips.append(caption)

        # ---------------- AUDIO MIX ----------------
        if os.path.exists(BGM_PATH):
            bgm = (
                AudioFileClip(BGM_PATH)
                .with_duration(total_duration)
                .multiply_volume(0.12)
            )
            final_audio = CompositeAudioClip([audio, bgm])
        else:
            final_audio = audio

        # ---------------- FINAL RENDER ----------------
        final_video = CompositeVideoClip([bg_video] + caption_clips).with_audio(
            final_audio
        )

        out_path = os.path.join(self.output_dir, f"FINAL_{task['_id']}.mp4")

        print("📦 Rendering final video...")
        try:
            final_video.write_videofile(
                out_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                threads=4,  # Use 4 threads for speed
                preset="fast",  # Faster encoding
            )

            self.db.collection.update_one(
                {"_id": task["_id"]},
                {"$set": {"status": "completed", "final_video_path": out_path}},
            )

            print(f"🎉 DONE: {out_path}")

        except Exception as e:
            print(f"❌ Render Failed: {e}")

        finally:
            # 3. RESOURCE CLEANUP
            # Close clips to free system resources (Fixes WinError 1450)
            try:
                final_video.close()
                audio.close()
                for clip in timeline_clips:
                    clip.close()
            except:
                pass
