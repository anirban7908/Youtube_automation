import os
import whisper
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
        # Use "base" or "tiny" model for speed
        self.model = whisper.load_model("base")

    def assemble(self):
        task = self.db.collection.find_one({"status": "ready_to_assemble"})
        if not task:
            print("📭 No tasks ready for assembly.")
            return

        print(f"🎬 Gapless Smart-Sync: {task['title']}")

        # 1. Load Audio
        audio = AudioFileClip(task["audio_path"])
        total_duration = audio.duration

        # 2. Transcribe
        print("🎙️ Analyzing audio timing...")
        result = self.model.transcribe(task["audio_path"], word_timestamps=True)
        segments = result["segments"]

        visual_scenes = task.get("visual_scenes", [])
        if not visual_scenes:
            print("❌ No visual scenes found.")
            return

        timeline_clips = []
        caption_clips = []

        # 3. Build Timeline (Video)
        for i, segment in enumerate(segments):
            start_time = segment["start"]

            # Gapless Logic: Extend clip to start of next sentence
            if i < len(segments) - 1:
                end_time = segments[i + 1]["start"]
            else:
                end_time = total_duration

            block_duration = end_time - start_time
            if block_duration <= 0:
                continue

            scene_index = i % len(visual_scenes)
            scene_data = visual_scenes[scene_index]
            clips = scene_data.get("clips", [])

            if not clips:
                continue

            num_clips = len(clips)
            clip_duration = block_duration / num_clips
            current_clip_start = start_time

            for clip_info in clips:
                path = clip_info["path"]
                try:
                    v = VideoFileClip(path).without_audio()

                    if v.duration < clip_duration:
                        v = v.with_effects([vfx.Loop(duration=clip_duration)])
                    else:
                        v = v.subclipped(0, clip_duration)

                    # Resize/Crop 9:16
                    v = v.resized(height=1920)
                    if v.w > 1080:
                        v = v.cropped(x_center=v.w / 2, width=1080)

                    v = v.with_start(current_clip_start).with_duration(clip_duration)
                    timeline_clips.append(v)
                    current_clip_start += clip_duration

                except Exception as e:
                    print(f"⚠️ Clip error: {path} -> {e}")

            # 4. Captions (FIXED POSITION - MOVED HIGHER)
            for word in segment["words"]:
                w_start = word["start"]
                w_end = max(word["end"], w_start + 0.1)

                # Padding spaces to protect outline
                safe_text = f" {word['word'].strip().upper()} "

                caption = (
                    TextClip(
                        text=safe_text,
                        font=FONT_PATH,
                        font_size=65,  # Slightly smaller font
                        color="yellow",
                        stroke_color="black",
                        stroke_width=4,
                    )
                    .with_start(w_start)
                    .with_duration(w_end - w_start)
                    # Position moved UP to Y=1000 (Safe zone)
                    .with_position(("center", 1000))
                )

                caption_clips.append(caption)

        # 5. Final Render
        if not timeline_clips:
            print("❌ Error: No video clips generated.")
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

        print("📦 Rendering synchronized video...")
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
                for c in timeline_clips:
                    c.close()
            except:
                pass
