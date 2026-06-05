import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

PROMPT_EXTRACT_TASKS = '''Ty - AI-assistent project-menedzhera. Proanaliziruj soobshchenie iz komandnogo chata i izvleki zadachi.

Dlya KAZHDOJ zadachi ukazhi:
- title: kratkoe nazvanie zadachi
- description: opisanie (esli est detali)
- assignee: imya ili @username otvetstvennogo (null esli ne yasno)
- deadline: dedlajn v formate ISO 8601 (null esli ne ukazan)
- priority: low/medium/high/critical (medium po umolchaniyu)
- confidence: uverennost 0-1

Esli zadach net - verni pustoj massiv.

Otvet TOLKO v formate JSON:
{
  "tasks": [
    {
      "title": "...",
      "description": "...",
      "assignee": "...",
      "deadline": "2026-06-10T17:00:00",
      "priority": "high",
      "confidence": 0.95
    }
  ],
  "summary": "kratkoe opisanie konteksta"
}

Soobshchenie:
{message}
'''

PROMPT_MEETING_SUMMARY = '''Ty - AI-assistent dlya vstrech. Proanaliziruj transkript vstrechi i sozdaj strukturirovannyj otchet.

Otvet TOLKO v formate JSON:
{
  "summary": "kratkoe rezume vstrechi (2-3 predlozheniya)",
  "key_points": ["klyuchevoj moment 1", "klyuchevoj moment 2"],
  "decisions": ["prinyatoe reshenie 1"],
  "action_items": [
    {
      "task": "opisanie zadachi",
      "assignee": "otvetstvennyj",
      "deadline": "2026-06-10",
      "priority": "high"
    }
  ],
  "risks": ["risk ili problema"],
  "next_meeting": "temy dlya sleduyushchej vstrechi"
}

Transkript:
{transcript}
'''

PROMPT_DAILY_REPORT = '''Ty - AI-assistent project-menedzhera. Proanaliziruj ezhednevnyj otchet sotrudnika i sopostav s zadachami iz kanban-doski.

Otvet TOLKO v formate JSON:
{
  "tasks_completed": ["id_zadachi_1", "id_zadachi_2"],
  "tasks_in_progress": ["id_zadachi_3"],
  "tasks_blocked": ["id_zadachi_4"],
  "new_tasks": [
    {
      "title": "novaya zadacha iz otchet",
      "description": "opisanie"
    }
  ],
  "status": "verified",
  "notes": "dopolnitelnye zametki"
}

Otchet sotrudnika:
{report}

Zadachi iz kanbana:
{kanban_tasks}
'''


class NLPEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def extract_tasks(self, message: str, context: str = "") -> Dict[str, Any]:
        if not self.client:
            return self._extract_tasks_fallback(message)

        try:
            prompt = PROMPT_EXTRACT_TASKS.format(message=message)
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            content = response.choices[0].message.content
            json_match = re.search(r'\\{.*\\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"tasks": [], "summary": ""}
        except Exception as e:
            print(f"NLP error: {e}")
            return self._extract_tasks_fallback(message)

    def _extract_tasks_fallback(self, message: str) -> Dict[str, Any]:
        tasks = []

        assignee = None
        assignee_match = re.search(r'@([a-zA-Z0-9_]+)', message)
        if assignee_match:
            assignee = assignee_match.group(1)

        deadline = None
        deadline_patterns = [
            r'(?:do|k|deadline|dedlajn)[:;]*\s*(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
            r'(?:zavtra|poslezavtra|segodnya|v ponedelnik|vo vtornik|v sredu|v chetverg|v pyatnitsu)',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                dl_str = match.group(1) if match.groups() else match.group(0)
                deadline = self._parse_date(dl_str)
                break

        lines = message.split('\n')
        for line in lines:
            line = line.strip()
            if any(kw in line.lower() for kw in ['sdelat', 'nuzhno', 'nado', 'zadacha', 'todo', 'task', 'vzyat']):
                task_title = re.sub(r'^(?:sdelat|nuzhno|nado|zadacha|todo|task|vzyat)[:;]*\s*', '', line, flags=re.IGNORECASE)
                if task_title and len(task_title) > 5:
                    tasks.append({
                        "title": task_title[:200],
                        "description": message[:500],
                        "assignee": assignee,
                        "deadline": deadline.isoformat() if deadline else None,
                        "priority": "medium",
                        "confidence": 0.6
                    })

        return {"tasks": tasks, "summary": "Izvlecheno cherez fallback"}

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        date_str = date_str.lower().strip()
        now = datetime.now()

        relative_dates = {
            'segodnya': now,
            'zavtra': now + timedelta(days=1),
            'poslezavtra': now + timedelta(days=2),
            'v ponedelnik': now + timedelta(days=(7 - now.weekday()) % 7),
            'vo vtornik': now + timedelta(days=(1 - now.weekday()) % 7),
            'v sredu': now + timedelta(days=(2 - now.weekday()) % 7),
            'v chetverg': now + timedelta(days=(3 - now.weekday()) % 7),
            'v pyatnitsu': now + timedelta(days=(4 - now.weekday()) % 7),
        }

        if date_str in relative_dates:
            return relative_dates[date_str].replace(hour=18, minute=0, second=0, microsecond=0)

        formats = ['%d.%m.%Y', '%d/%m/%Y', '%d.%m.%y', '%d/%m/%y', '%Y-%m-%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).replace(hour=18, minute=0)
            except ValueError:
                continue

        return None

    async def summarize_meeting(self, transcript: str) -> Dict[str, Any]:
        if not self.client or not transcript:
            return {
                "summary": "Transkript otsutstvuet ili API nedostupen",
                "key_points": [],
                "decisions": [],
                "action_items": [],
                "risks": [],
                "next_meeting": ""
            }

        try:
            prompt = PROMPT_MEETING_SUMMARY.format(transcript=transcript[:8000])
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            content = response.choices[0].message.content
            json_match = re.search(r'\\{.*\\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"summary": content, "key_points": [], "decisions": [], "action_items": [], "risks": [], "next_meeting": ""}
        except Exception as e:
            print(f"Meeting summary error: {e}")
            return {
                "summary": "Oshibka obrabotki transkripta",
                "key_points": [],
                "decisions": [],
                "action_items": [],
                "risks": [],
                "next_meeting": ""
            }

    async def analyze_daily_report(self, report: str, kanban_tasks: List[Dict]) -> Dict[str, Any]:
        if not self.client:
            return {"tasks_completed": [], "tasks_in_progress": [], "tasks_blocked": [], "new_tasks": [], "status": "pending", "notes": ""}

        try:
            tasks_json = json.dumps(kanban_tasks, ensure_ascii=False, default=str)
            prompt = PROMPT_DAILY_REPORT.format(report=report, kanban_tasks=tasks_json)
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            content = response.choices[0].message.content
            json_match = re.search(r'\\{.*\\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"status": "pending", "notes": content}
        except Exception as e:
            print(f"Daily report analysis error: {e}")
            return {"status": "pending", "notes": str(e)}

    async def generate_reminder_message(self, task_title: str, deadline: datetime, assignee: str) -> str:
        time_left = deadline - datetime.now()
        hours_left = time_left.total_seconds() / 3600

        if hours_left < 0:
            return f"⏰ @{assignee} zadacha **{task_title}** prosrochena! Nuzhno srochno obnovit status."
        elif hours_left < 2:
            return f"⚠️ @{assignee} zadacha **{task_title}** cherez {int(hours_left)} chasov!"
        elif hours_left < 24:
            return f"📋 @{assignee} napominayu: zadacha **{task_title}** zavtra ({deadline.strftime('%d.%m %H:%M')})."
        else:
            return f"📅 @{assignee} zadacha **{task_title}** -- dedlajn {deadline.strftime('%d.%m.%Y %H:%M')}."


nlp_engine = NLPEngine()
