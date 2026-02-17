import os
import whisper
import moviepy.video.fx as vfx
from moviepy import (
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)
from core.db_manager import DBManager

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"


class VideoAssembler:
    def __init__(self):
        self.db = DBManager()
        self.model = whisper.load_model("base")

    def assemble(self):
        task = self.db.collection.find_one({"status": "ready_to_assemble"})
        if not task:
            return

        scenes = task.get("script_data", [])
        folder = task["folder_path"]
        print(f"🎞️ Assembling {len(scenes)} synchronized segments...")

        final_clips = []

        for i, scene in enumerate(scenes):
            # 1. Audio for this specific segment
            audio_path = scene["audio_path"]
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration

            # 2. Images for this specific segment
            img_paths = scene["image_paths"]
            num_images = len(img_paths)
            img_duration = duration / num_images

            scene_clips = []
            for img_path in img_paths:
                try:
                    clip = (
                        ImageClip(img_path)
                        .with_duration(img_duration)
                        .resized(height=1920)
                        .with_effects([vfx.Resize(lambda t: 1 + 0.04 * t)])
                    )  # Zoom effect

                    # Center Crop to fill 9:16
                    if clip.w < 1080:
                        clip = clip.resized(width=1080)
                    clip = clip.cropped(
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                        width=1080,
                        height=1920,
                    )

                    scene_clips.append(clip)
                except:
                    pass

            if scene_clips:
                # Combine images for this scene
                scene_video = concatenate_videoclips(scene_clips).with_audio(audio_clip)
                final_clips.append(scene_video)

        # 3. Combine ALL Scenes
        full_video = concatenate_videoclips(final_clips)

        # 4. Generate Subtitles (One pass over the full audio? No, easier to do full pass)
        # We need to save the full audio first to transcribe it correctly
        full_audio_path = os.path.join(folder, "FULL_AUDIO_TEMP.mp3")
        full_video.audio.write_audiofile(full_audio_path)

        print("📝 Generating Captions...")
        result = self.model.transcribe(full_audio_path, word_timestamps=True)
        caption_clips = []

        for segment in result["segments"]:
            for word in segment["words"]:
                txt = (
                    TextClip(
                        text=word["word"].strip().upper(),
                        font=FONT_PATH,
                        font_size=75,  # Increased size slightly for readability
                        color="yellow",
                        stroke_color="black",
                        stroke_width=4,
                        # bg_color="#373636FF",  # Semi-transparent black box container
                        method="caption",
                        size=(1000, None),
                        margin=(
                            20,
                            15,
                        ),  # THE FIX: Adds 15px vertical padding so text isn't cut off
                    )
                    .with_start(word["start"])
                    .with_duration(word["end"] - word["start"])
                    .with_position(
                        ("center", 1600)
                    )  # Moved slightly lower to look better
                )
                caption_clips.append(txt)
        final_export = CompositeVideoClip(
            [full_video] + caption_clips, size=(1080, 1920)
        )

        out_path = os.path.join(folder, "FINAL_VIDEO.mp4")
        final_export.write_videofile(out_path, fps=24, logger="bar")

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"status": "ready_to_upload", "final_video_path": out_path}},
        )
        print(f"🎉 Synchronized Video Ready: {out_path}")
