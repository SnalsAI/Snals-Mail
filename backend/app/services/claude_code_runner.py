"""
Servizio per eseguire Claude Code e catturare l'output.
Permette di risolvere bug automaticamente con AI.
"""

import asyncio
import json
import os
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Path al progetto (dentro Docker è /project per accedere a backend+frontend)
PROJECT_PATH = os.environ.get("PROJECT_PATH", "/project")


class ClaudeCodeRunner:
    """Runner per eseguire Claude Code come subprocess."""

    def __init__(self, project_path: str = PROJECT_PATH):
        self.project_path = project_path
        self.current_process: Optional[asyncio.subprocess.Process] = None

    def _parse_json_line(self, text: str) -> Optional[Dict[str, Any]]:
        """Parsa una linea JSON e restituisce un evento formattato."""
        if not text.strip():
            return None

        try:
            data = json.loads(text)
            event_type = data.get("type", "unknown")

            if event_type == "system":
                subtype = data.get("subtype", "")
                if subtype == "init":
                    return {
                        "type": "system",
                        "timestamp": datetime.now().isoformat(),
                        "message": f"Sessione avviata - Model: {data.get('model', 'unknown')}"
                    }
                return {
                    "type": "system",
                    "timestamp": datetime.now().isoformat(),
                    "message": data.get("message", subtype or "system event")
                }

            elif event_type == "assistant":
                message_data = data.get("message", {})
                content = message_data.get("content", [])

                text_parts = []
                tool_uses = []

                for c in content:
                    c_type = c.get("type")
                    if c_type == "text":
                        txt = c.get("text", "")
                        if txt:
                            text_parts.append(txt)
                    elif c_type == "tool_use":
                        tool_name = c.get("name", "unknown")
                        tool_input = c.get("input", {})
                        # Riduci input per leggibilità
                        input_summary = {}
                        for k, v in tool_input.items():
                            if isinstance(v, str) and len(v) > 80:
                                input_summary[k] = v[:80] + "..."
                            else:
                                input_summary[k] = v
                        tool_uses.append({"tool": tool_name, "input": input_summary})

                if text_parts or tool_uses:
                    return {
                        "type": "assistant",
                        "timestamp": datetime.now().isoformat(),
                        "text": "\n".join(text_parts) if text_parts else None,
                        "tools": tool_uses if tool_uses else None
                    }
                return None

            elif event_type == "result":
                result_text = data.get("result", "")
                if isinstance(result_text, str) and len(result_text) > 400:
                    result_text = result_text[:400] + "..."
                return {
                    "type": "result",
                    "timestamp": datetime.now().isoformat(),
                    "success": not data.get("is_error", False),
                    "result": result_text,
                    "duration": data.get("duration_ms"),
                    "cost": data.get("total_cost_usd")
                }

            elif event_type == "user":
                content = data.get("message", {}).get("content", [])
                tool_results = []
                for c in content:
                    if c.get("type") == "tool_result":
                        result_content = c.get("content", "")
                        if isinstance(result_content, str):
                            if len(result_content) > 200:
                                result_content = result_content[:200] + "..."
                            tool_results.append(result_content)
                        elif isinstance(result_content, list):
                            for item in result_content[:2]:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    txt = item.get("text", "")[:150]
                                    tool_results.append(txt)

                if tool_results:
                    return {
                        "type": "tool_result",
                        "timestamp": datetime.now().isoformat(),
                        "results": tool_results
                    }
                return None

            else:
                # Altri tipi - ignora quelli vuoti
                msg = data.get("message", data.get("result", data.get("subtype", "")))
                if isinstance(msg, dict):
                    msg = json.dumps(msg)[:150]
                elif isinstance(msg, str) and len(msg) > 150:
                    msg = msg[:150] + "..."

                if msg:
                    return {
                        "type": event_type,
                        "timestamp": datetime.now().isoformat(),
                        "message": str(msg)
                    }
                return None

        except json.JSONDecodeError:
            # Non è JSON valido, potrebbe essere output testuale
            if text.strip():
                return {
                    "type": "text",
                    "timestamp": datetime.now().isoformat(),
                    "message": text[:400] if len(text) > 400 else text
                }
            return None
        except Exception as e:
            logger.warning(f"Errore parsing linea: {e}")
            return None

    async def run_prompt(
        self,
        prompt: str,
        timeout: int = 300
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Esegue Claude Code con un prompt e genera output in streaming."""

        cmd = [
            "claude",
            "--print",
            "--output-format", "stream-json",
            "--verbose",  # Richiesto con stream-json e --print
            "-p", prompt
        ]

        yield {
            "type": "start",
            "timestamp": datetime.now().isoformat(),
            "message": "Avvio Claude Code...",
            "prompt": prompt[:150] + "..." if len(prompt) > 150 else prompt
        }

        try:
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_path,
                env={**os.environ, "CLAUDE_CODE_NO_COLOR": "1"}
            )

            yield {
                "type": "running",
                "timestamp": datetime.now().isoformat(),
                "message": "Claude Code in esecuzione..."
            }

            # Buffer per accumulate dati parziali
            buffer = b""

            while True:
                try:
                    # Leggi chunk con timeout
                    chunk = await asyncio.wait_for(
                        self.current_process.stdout.read(4096),
                        timeout=45
                    )

                    if not chunk:
                        # EOF raggiunto
                        break

                    buffer += chunk

                    # Processa tutte le linee complete nel buffer
                    while b'\n' in buffer:
                        line_bytes, buffer = buffer.split(b'\n', 1)
                        line_text = line_bytes.decode('utf-8', errors='replace').strip()

                        if line_text:
                            parsed = self._parse_json_line(line_text)
                            if parsed:
                                yield parsed

                except asyncio.TimeoutError:
                    yield {
                        "type": "waiting",
                        "timestamp": datetime.now().isoformat(),
                        "message": "In attesa di risposta..."
                    }
                    continue

            # Processa eventuale contenuto rimasto nel buffer
            if buffer:
                remaining = buffer.decode('utf-8', errors='replace').strip()
                if remaining:
                    for line in remaining.split('\n'):
                        if line.strip():
                            parsed = self._parse_json_line(line.strip())
                            if parsed:
                                yield parsed

            # Attendi che il processo termini
            try:
                await asyncio.wait_for(self.current_process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self.current_process.terminate()
                try:
                    await asyncio.wait_for(self.current_process.wait(), timeout=5)
                except:
                    self.current_process.kill()

            # Leggi stderr per eventuali errori
            if self.current_process.stderr:
                stderr_data = await self.current_process.stderr.read()
                if stderr_data:
                    stderr_text = stderr_data.decode('utf-8', errors='replace').strip()
                    # Mostra solo errori significativi
                    if stderr_text and ('error' in stderr_text.lower() or 'exception' in stderr_text.lower()):
                        yield {
                            "type": "stderr",
                            "timestamp": datetime.now().isoformat(),
                            "message": stderr_text[:300]
                        }

            exit_code = self.current_process.returncode or 0

            yield {
                "type": "complete",
                "timestamp": datetime.now().isoformat(),
                "exit_code": exit_code,
                "success": exit_code == 0,
                "message": "Completato" if exit_code == 0 else f"Exit code: {exit_code}"
            }

        except asyncio.CancelledError:
            if self.current_process:
                self.current_process.terminate()
            yield {
                "type": "cancelled",
                "timestamp": datetime.now().isoformat(),
                "message": "Operazione annullata"
            }
            raise

        except Exception as e:
            logger.error(f"Errore esecuzione Claude Code: {e}", exc_info=True)
            yield {
                "type": "error",
                "timestamp": datetime.now().isoformat(),
                "message": str(e)
            }

        finally:
            self.current_process = None

    def cancel(self):
        """Annulla l'esecuzione corrente."""
        if self.current_process:
            try:
                self.current_process.terminate()
                return True
            except:
                pass
        return False


def build_bug_fix_prompt(bug: Dict[str, Any]) -> str:
    """Costruisce il prompt per risolvere un bug."""
    prompt = f"""Risolvi questo bug segnalato dall'utente:

## Bug #{bug.get('id')}
**Descrizione:** {bug.get('descrizione')}
**Pagina:** {bug.get('pagina', 'N/A')}
**Viewport:** {bug.get('viewport', 'N/A')}

"""

    if bug.get('console_errors'):
        prompt += f"**Errori Console:**\n```\n{json.dumps(bug['console_errors'], indent=2)}\n```\n\n"

    if bug.get('email_id'):
        prompt += f"**Email correlata:** ID {bug['email_id']}\n\n"

    if bug.get('azione_id'):
        prompt += f"**Azione correlata:** ID {bug['azione_id']}\n\n"

    prompt += """## Istruzioni
1. Analizza il bug e identifica la causa
2. Trova i file coinvolti
3. Applica la fix necessaria
4. Verifica che la fix sia corretta
5. Rispondi con un riepilogo di cosa hai fatto

Non chiedere conferme, procedi direttamente con la risoluzione.
"""

    return prompt


# Singleton con lock per thread safety
_runner_instance: Optional[ClaudeCodeRunner] = None
_runner_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None


def get_claude_runner() -> ClaudeCodeRunner:
    """Restituisce l'istanza singleton del runner."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ClaudeCodeRunner()
    return _runner_instance
