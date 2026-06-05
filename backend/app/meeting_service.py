import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from app.config import get_settings
from app.nlp_engine import nlp_engine

settings = get_settings()


class MeetingService:
    def __init__(self):
        self.active_meetings = {}  # chat_id -> meeting_data
        self.recordings_dir = "/app/data/recordings"
        os.makedirs(self.recordings_dir, exist_ok=True)

    async def schedule_meeting(self, chat_id: str, title: str, platform: str = "yandex_telemost",
                               meeting_url: str = None, scheduled_at: datetime = None,
                               duration: int = 60) -> Dict[str, Any]:
        meeting = {
            "id": f"meet_{chat_id}_{int(datetime.now().timestamp())}",
            "chat_id": chat_id,
            "title": title,
            "platform": platform,
            "meeting_url": meeting_url,
            "scheduled_at": scheduled_at or (datetime.now() + timedelta(minutes=10)),
            "duration_minutes": duration,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        return meeting

    async def start_meeting_simulation(self, chat_id: str, title: str) -> Dict[str, Any]:
        meeting = {
            "id": f"sim_{chat_id}_{int(datetime.now().timestamp())}",
            "chat_id": chat_id,
            "title": title,
            "platform": "simulated",
            "status": "active",
            "started_at": datetime.now().isoformat(),
            "transcript_segments": []
        }
        self.active_meetings[chat_id] = meeting
        return meeting

    async def add_transcript_segment(self, chat_id: str, speaker: str, text: str):
        if chat_id in self.active_meetings:
            self.active_meetings[chat_id]["transcript_segments"].append({
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.now().isoformat()
            })

    async def end_meeting(self, chat_id: str) -> Dict[str, Any]:
        if chat_id not in self.active_meetings:
            return {"error": "No active meeting"}

        meeting = self.active_meetings[chat_id]
        meeting["status"] = "completed"
        meeting["ended_at"] = datetime.now().isoformat()

        # Build transcript
        transcript_parts = []
        for seg in meeting.get("transcript_segments", []):
            transcript_parts.append(f"{seg['speaker']}: {seg['text']}")

        full_transcript = "\n".join(transcript_parts)
        meeting["transcript"] = full_transcript

        # Generate summary via NLP
        summary = await nlp_engine.summarize_meeting(full_transcript)
        meeting["summary"] = summary

        # Save to file
        filename = f"{self.recordings_dir}/meeting_{meeting['id']}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(meeting, f, ensure_ascii=False, indent=2, default=str)

        del self.active_meetings[chat_id]
        return meeting

    async def get_meeting_summary(self, meeting_id: str) -> Optional[Dict]:
        filename = f"{self.recordings_dir}/meeting_{meeting_id}.json"
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    async def simulate_yandex_telemost(self, chat_id: str, bot) -> Dict[str, Any]:
        # Simulate Yandex Telemost integration
        # In real scenario, this would use browser automation or API
        meeting = await self.start_meeting_simulation(chat_id, "Yandex Telemost Meeting")

        # Simulate some conversation
        demo_transcript = [
            ("Ivan", "Privet vsem, nachinaem planirovanie sprinta."),
            ("Maria", "Ya gotova vzhat zadachu po integracii s API."),
            ("Alex", "Nuzhno sdelat refactoring bazy dannyh do pyatnitsy."),
            ("Ivan", "Horosho, deadline po refactoringu -- 10 iyunya."),
            ("Maria", "Ya pomogu s testirovaniem."),
            ("Alex", "Esche nuzhno obnovit dokumentaciyu."),
            ("Ivan", "Dokumentaciya -- na Mariu, deadline do sredy."),
        ]

        for speaker, text in demo_transcript:
            await self.add_transcript_segment(chat_id, speaker, text)
            await asyncio.sleep(0.5)

        result = await self.end_meeting(chat_id)
        return result

    async def process_audio_file(self, audio_path: str, chat_id: str = None) -> Dict[str, Any]:
        # Use Whisper for transcription
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, language="ru")

            transcript = result["text"]

            if chat_id:
                meeting = await self.start_meeting_simulation(chat_id, "Audio Meeting")
                await self.add_transcript_segment(chat_id, "Speaker", transcript)
                return await self.end_meeting(chat_id)

            return {"transcript": transcript, "language": result.get("language", "ru")}
        except Exception as e:
            return {"error": f"Transcription failed: {str(e)}", "transcript": ""}

    async def connect_to_telemost(self, meeting_url: str) -> Dict[str, Any]:
        # Placeholder for actual Yandex Telemost integration
        # Would require browser automation (Selenium/Playwright) or official API
        return {
            "status": "simulated",
            "message": "Yandex Telemost integration requires browser automation or official API access",
            "meeting_url": meeting_url,
            "note": "For hackathon: use /simulate_meeting command for demo"
        }


meeting_service = MeetingService()
