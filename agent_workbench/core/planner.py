from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hardware_knowledge import HardwareKnowledge
from .param_extractor import ExtractedParameters, extract_parameters
from .project_scanner import scan_project
from .utils import local_now_tag, render_template

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc


@dataclass
class TaskTemplate:
    payload: dict[str, Any]
    path: Path

    @property
    def template_id(self) -> str:
        return str(self.payload.get("id", self.path.stem))

    @property
    def keywords(self) -> list[str]:
        return [str(item).strip().lower() for item in self.payload.get("keywords", []) if str(item).strip()]

    @property
    def exclude_keywords(self) -> list[str]:
        return [str(item).strip().lower() for item in self.payload.get("exclude_keywords", []) if str(item).strip()]

    @property
    def priority(self) -> int:
        return int(self.payload.get("priority", 0))


def _render_value(value: Any, values: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return render_template(value, values)
    if isinstance(value, list):
        return [_render_value(item, values) for item in value]
    if isinstance(value, dict):
        return {key: _render_value(item, values) for key, item in value.items()}
    return value


def _dedupe_strings(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def _normalize_stable_strings(raw_items: list[Any], defaults: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            normalized.append(item)
            continue
        if isinstance(item, dict) and len(item) == 1:
            key, value = next(iter(item.items()))
            if value in {None, ""}:
                normalized.append(str(key))
                continue
        if item is None:
            continue
        normalized.append(str(item))
    merged = normalized or defaults
    return _dedupe_strings([item for item in merged if str(item).strip()])


def _build_default_shell_steps() -> list[dict[str, Any]]:
    return [
        {
            "name": "编译验证",
            "command": "./agent_workbench.bat build --json",
            "success_criteria": "exit_code == 0",
            "on_failure": {
                "max_retries": 3,
                "retry_strategy": "先读取 errors[0] 与 suggested_fix，再做最小修复并重试当前步骤。",
                "retry_command": "./agent_workbench.bat fix-build --json",
            },
        },
        {
            "name": "UART CLI 回归验证",
            "command": "./agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json",
            "success_criteria": "transcript contains ready banner and prompt",
        },
    ]


def _region_marker(snapshot: dict[str, Any], name: str, file_path: str) -> str:
    for region in snapshot.get("user_code_regions", []):
        if region.get("name") == name and region.get("file") == file_path:
            return str(region.get("begin_marker", ""))
    return f"/* {name} */"


def _command_names(snapshot: dict[str, Any]) -> list[str]:
    return [str(item).strip().lower() for item in snapshot.get("uart", {}).get("help_commands", []) if str(item).strip()]


def _handle_names(snapshot: dict[str, Any]) -> set[str]:
    return {str(item.get("name", "")).strip() for item in snapshot.get("existing_handles", []) if str(item.get("name", "")).strip()}


class Planner:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.templates_dir = Path(cfg["planner"]["templates_dir_path"])
        knowledge_root = Path(
            cfg.get("planner", {}).get("hardware_knowledge_dir_path", self.templates_dir.parent / "hardware_knowledge")
        )
        self.hardware = HardwareKnowledge(knowledge_root)

    def _load_templates(self) -> list[TaskTemplate]:
        templates: list[TaskTemplate] = []
        if not self.templates_dir.exists():
            return templates
        for path in sorted(self.templates_dir.glob("*.yaml")):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            templates.append(TaskTemplate(payload=payload, path=path))
        return templates

    def _match_template(self, user_request: str) -> tuple[TaskTemplate | None, list[str]]:
        normalized = user_request.lower()
        best_template: TaskTemplate | None = None
        best_keywords: list[str] = []
        best_score = -10**9
        for template in self._load_templates():
            if any(keyword in normalized for keyword in template.exclude_keywords):
                continue
            matched = [keyword for keyword in template.keywords if keyword in normalized]
            if not matched:
                continue
            score = len(matched) * 100 + template.priority
            if score > best_score:
                best_score = score
                best_template = template
                best_keywords = matched
        return best_template, best_keywords

    def _fallback_template(self, user_request: str) -> TaskTemplate:
        debug_keywords = ["debug", "调试", "诊断", "分析", "异常", "故障", "error", "panic", "排查"]
        mode = "debug" if any(keyword in user_request.lower() for keyword in debug_keywords) else "feature"
        payload: dict[str, Any] = {
            "id": f"fallback_{mode}",
            "mode": mode,
            "description": "围绕用户自然语言需求生成的通用结构化执行计划。",
            "read_files": [
                {"file": "Core/Src/main.c", "why": "理解主初始化流程与现有用户代码区域。"},
                {"file": "Core/Inc/main.h", "why": "确认外设句柄、宏定义与可复用声明位置。"},
            ],
            "edit_files": [{"file": "Core/Src/main.c", "instructions": "依据 `{user_request}` 做最小安全改动。"}],
            "shell_steps": _build_default_shell_steps(),
            "stable_strings": [self.cfg["uart"].get("ready_banner", ""), self.cfg["uart"].get("prompt", "")],
            "forbidden_operations": [
                "删除已有 CLI 命令",
                "修改 ready banner 或 prompt 字符串",
                "改动 Drivers 目录",
            ],
        }
        return TaskTemplate(payload=payload, path=self.templates_dir / f"{payload['id']}.yaml")

    def _template_values(self, user_request: str, params: ExtractedParameters) -> dict[str, Any]:
        values = {
            "user_request": user_request,
            "project_name": self.cfg["project"]["name"],
            "ready_banner": self.cfg["uart"].get("ready_banner", ""),
            "prompt": self.cfg["uart"].get("prompt", ""),
            "uart_port": self.cfg["uart"].get("port", ""),
            "build_dir": self.cfg["project"].get("build_dir_path", ""),
        }
        for key, value in params.to_dict().items():
            values[key] = "" if value is None else value
        return values

    def _default_hardware_context(self, params: ExtractedParameters, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "clock": self.hardware.default_clock_context(),
            "user_code_regions": snapshot.get("user_code_regions", []),
            "existing_handles": snapshot.get("existing_handles", []),
            "available_cli_commands": snapshot.get("uart", {}).get("help_commands", []),
            "parameter_hints": params.to_dict(),
        }

    def _build_hardware_context(
        self,
        template_id: str,
        params: ExtractedParameters,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        context = self._default_hardware_context(params, snapshot)
        if template_id == "timer_pwm":
            context.update(
                self.hardware.build_pwm_context(
                    frequency_hz=params.frequency_hz,
                    duty_percent=params.duty_percent,
                    pin=params.pin,
                    requested_timer=params.timer,
                )
            )
        return context

    def _build_pwm_hints(
        self,
        params: ExtractedParameters,
        snapshot: dict[str, Any],
        hardware_context: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        timer_cfg = hardware_context.get("timer_config", {})
        pin_mapping = hardware_context.get("pin_mapping", {})
        handle_name = str(timer_cfg.get("handle_name", "")).strip()
        timer_name = str(timer_cfg.get("timer", "")).strip()
        channel = str(timer_cfg.get("channel", "")).strip()
        pin = str(pin_mapping.get("requested_pin", "")).strip()
        gpio_port = str(pin_mapping.get("gpio_port", "")).strip()
        gpio_pin_define = str(pin_mapping.get("gpio_pin_define", "")).strip()
        handle_exists = handle_name in _handle_names(snapshot)

        main_c_region_pv = _region_marker(snapshot, "USER CODE BEGIN PV", "Core/Src/main.c")
        main_c_region_pfp = _region_marker(snapshot, "USER CODE BEGIN PFP", "Core/Src/main.c")
        main_c_region_init = _region_marker(snapshot, "USER CODE BEGIN 2", "Core/Src/main.c")
        main_c_region_functions = _region_marker(snapshot, "USER CODE BEGIN 4", "Core/Src/main.c")
        main_h_region = _region_marker(snapshot, "USER CODE BEGIN EFP", "Core/Inc/main.h")

        function_name = f"MX_{timer_name}_PWM_Init" if timer_name else "MX_TIMx_PWM_Init"
        function_body = "\n".join(
            [
                f"static void {function_name}(void)",
                "{",
                "  TIM_OC_InitTypeDef sConfigOC = {0};",
                "  GPIO_InitTypeDef GPIO_InitStruct = {0};",
                "",
                f"  __HAL_RCC_{timer_name}_CLK_ENABLE();" if timer_name else "  /* enable timer clock here */",
                f"  __HAL_RCC_{gpio_port}_CLK_ENABLE();" if gpio_port else "  /* enable GPIO clock here */",
                "",
                f"  {handle_name}.Instance = {timer_name};" if handle_name and timer_name else "  /* configure timer instance */",
                f"  {handle_name}.Init.Prescaler = {timer_cfg.get('prescaler', 0)};" if handle_name else "  /* configure prescaler */",
                f"  {handle_name}.Init.CounterMode = TIM_COUNTERMODE_UP;" if handle_name else "  /* configure counter mode */",
                f"  {handle_name}.Init.Period = {timer_cfg.get('period', 0)};" if handle_name else "  /* configure period */",
                f"  {handle_name}.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;" if handle_name else "  /* configure clock division */",
                f"  {handle_name}.Init.RepetitionCounter = 0;" if handle_name else "  /* configure repetition counter */",
                f"  if (HAL_TIM_PWM_Init(&{handle_name}) != HAL_OK)" if handle_name else "  if (HAL_TIM_PWM_Init(&htimX) != HAL_OK)",
                "  {",
                "    Error_Handler();",
                "  }",
                "",
                "  sConfigOC.OCMode = TIM_OCMODE_PWM1;",
                f"  sConfigOC.Pulse = {timer_cfg.get('ccr', 0)};",
                "  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;",
                "  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;",
                f"  if (HAL_TIM_PWM_ConfigChannel(&{handle_name}, &sConfigOC, {channel}) != HAL_OK)" if handle_name and channel else "  /* configure PWM channel here */",
                "  {",
                "    Error_Handler();",
                "  }",
                "",
                f"  GPIO_InitStruct.Pin = {gpio_pin_define};" if gpio_pin_define else "  /* select GPIO pin here */",
                "  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;",
                "  GPIO_InitStruct.Pull = GPIO_NOPULL;",
                "  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;",
                f"  HAL_GPIO_Init({gpio_port}, &GPIO_InitStruct);" if gpio_port else "  /* initialize GPIO here */",
                "",
                f"  if (HAL_TIM_PWM_Start(&{handle_name}, {channel}) != HAL_OK)" if handle_name and channel else "  /* start PWM here */",
                "  {",
                "    Error_Handler();",
                "  }",
                "}",
            ]
        )

        main_c_hints: list[dict[str, Any]] = []
        if handle_name:
            if handle_exists:
                main_c_hints.append(
                    {
                        "type": "reuse_existing_handle",
                        "target_region": main_c_region_pv,
                        "handle_name": handle_name,
                        "reason": f"{handle_name} 已存在，优先复用现有句柄而不是重复声明。",
                    }
                )
            else:
                main_c_hints.append(
                    {
                        "type": "add_private_variable",
                        "target_region": main_c_region_pv,
                        "code_template": f"TIM_HandleTypeDef {handle_name};",
                        "reason": "为 PWM 输出添加定时器句柄。",
                    }
                )

        main_c_hints.extend(
            [
                {
                    "type": "add_function_prototype",
                    "target_region": main_c_region_pfp,
                    "code_template": f"static void {function_name}(void);",
                    "reason": "在用户函数声明区暴露 PWM 初始化入口。",
                },
                {
                    "type": "add_function",
                    "target_region": main_c_region_functions,
                    "function_name": function_name,
                    "code_template": function_body,
                    "parameter_hints": {
                        "pin": pin,
                        "timer": timer_name,
                        "channel": channel,
                        "frequency_hz": timer_cfg.get("target_frequency_hz"),
                        "prescaler": timer_cfg.get("prescaler"),
                        "period": timer_cfg.get("period"),
                        "ccr": timer_cfg.get("ccr"),
                    },
                    "reason": "增加一个确定性的 PWM 初始化辅助函数。",
                },
                {
                    "type": "add_call",
                    "target_region": main_c_region_init,
                    "code_template": f"{function_name}();",
                    "reason": "在主初始化阶段启动 PWM。",
                },
            ]
        )

        main_h_hints: list[dict[str, Any]] = []
        if handle_name:
            main_h_hints.append(
                {
                    "type": "add_extern_declaration",
                    "target_region": main_h_region,
                    "code_template": f"extern TIM_HandleTypeDef {handle_name};",
                    "reason": "对外暴露定时器句柄声明，方便跨文件引用。",
                }
            )

        return {
            "Core/Src/main.c": main_c_hints,
            "Core/Inc/main.h": main_h_hints,
        }

    def _build_cli_command_hints(
        self,
        user_request: str,
        params: ExtractedParameters,
        snapshot: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        command_name = params.cli_command_name or "new_command"
        existing_commands = _command_names(snapshot)
        main_c_region = "existing CLI command table"
        main_h_region = _region_marker(snapshot, "USER CODE BEGIN EFP", "Core/Inc/main.h")
        handler_name = "AppCli_" + "".join(part.capitalize() for part in command_name.split("_"))
        request_desc = user_request.replace("\n", " ").strip()

        command_body = "\n".join(
            [
                f"static void {handler_name}(CliContext *cli, int argc, char **argv)",
                "{",
                "  (void)argc;",
                "  (void)argv;",
                "",
                '  Cli_Printf(cli, "%s\\r\\n", "implement command behavior here");',
                "}",
            ]
        )

        return {
            "Core/Src/app_cli_commands.c": [
                {
                    "type": "add_forward_declaration",
                    "target_region": main_c_region,
                    "code_template": f"static void {handler_name}(CliContext *cli, int argc, char **argv);",
                    "reason": "在命令表之前声明新的处理函数。",
                },
                {
                    "type": "add_command_table_entry",
                    "target_region": main_c_region,
                    "code_template": f'{{ "{command_name}", "Implement: {request_desc}", "{command_name}", {handler_name} }},',
                    "reason": "把新命令注册到 app_cli_commands[] 表。",
                    "replace_existing": command_name in existing_commands,
                },
                {
                    "type": "add_function",
                    "target_region": "end of app_cli_commands.c",
                    "function_name": handler_name,
                    "code_template": command_body,
                    "reason": "添加命令处理函数骨架，并由后续实现步骤按需求补充具体逻辑。",
                },
            ],
            "Core/Inc/app_cli_commands.h": [
                {
                    "type": "review_header_exports",
                    "target_region": main_h_region,
                    "reason": "如果命令实现需要新增对外声明，再补最小头文件改动；否则保持头文件不变。",
                }
            ],
        }

    def _build_generic_hints(
        self,
        user_request: str,
        params: ExtractedParameters,
        edit_files: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        hints: dict[str, list[dict[str, Any]]] = {}
        for item in edit_files:
            file_path = str(item.get("file", "")).strip()
            if not file_path:
                continue
            hints[file_path] = [
                {
                    "type": "apply_structured_request",
                    "request": user_request,
                    "parameter_hints": params.to_dict(),
                    "reason": "依据结构化提取结果做最小安全改动。",
                }
            ]
        return hints

    def _build_code_change_hints(
        self,
        template_id: str,
        user_request: str,
        params: ExtractedParameters,
        snapshot: dict[str, Any],
        hardware_context: dict[str, Any],
        edit_files: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        if template_id == "timer_pwm":
            return self._build_pwm_hints(params, snapshot, hardware_context)
        if template_id == "uart_cli_command":
            return self._build_cli_command_hints(user_request, params, snapshot)
        return self._build_generic_hints(user_request, params, edit_files)

    def _build_notes(
        self,
        template_id: str,
        params: ExtractedParameters,
        snapshot: dict[str, Any],
        hardware_context: dict[str, Any],
    ) -> list[str]:
        notes: list[str] = []
        existing_handles = _handle_names(snapshot)
        existing_commands = _command_names(snapshot)

        if template_id == "timer_pwm":
            timer_cfg = hardware_context.get("timer_config", {})
            handle_name = str(timer_cfg.get("handle_name", "")).strip()
            pin_mapping = hardware_context.get("pin_mapping", {})
            if handle_name and handle_name in existing_handles:
                notes.append(f"⚠️ {handle_name} 已存在，建议复用现有句柄而不是重复声明。")
            if params.pin and not pin_mapping.get("recommended"):
                notes.append(f"⚠️ 未在静态硬件知识库中找到 {params.pin} 的 PWM 映射，请人工确认芯片引脚复用。")

        if template_id == "uart_cli_command" and params.cli_command_name:
            if params.cli_command_name.lower() in existing_commands:
                notes.append(f"⚠️ CLI 命令 `{params.cli_command_name}` 已存在，此次应视为修改/增强而不是新增。")

        return notes

    def _build_understanding(
        self,
        template_id: str,
        payload: dict[str, Any],
        params: ExtractedParameters,
        hardware_context: dict[str, Any],
    ) -> str:
        if template_id == "timer_pwm":
            timer_cfg = hardware_context.get("timer_config", {})
            pin_mapping = hardware_context.get("pin_mapping", {})
            pin = pin_mapping.get("requested_pin") or params.pin or "指定引脚"
            channel = pin_mapping.get("recommended") or timer_cfg.get("channel") or "可用 PWM 通道"
            frequency_hz = timer_cfg.get("target_frequency_hz") or params.frequency_hz or 1000
            duty_percent = timer_cfg.get("duty_percent") or params.duty_percent or 50
            return f"在 {pin} 上使用 {channel} 输出约 {frequency_hz}Hz PWM，占空比 {duty_percent}%。"

        if template_id == "uart_cli_command":
            command_name = params.cli_command_name or "新命令"
            return f"为现有 UART CLI 添加或增强 `{command_name}` 命令，并保持 ready banner 与 prompt 稳定。"

        return str(payload.get("description", "基于用户自然语言需求生成的结构化执行计划。"))

    def plan(self, user_request: str) -> dict[str, Any]:
        snapshot = scan_project(self.cfg)
        params = extract_parameters(user_request)
        template, matched_keywords = self._match_template(user_request)
        if template is None:
            template = self._fallback_template(user_request)

        payload = _render_value(template.payload, self._template_values(user_request, params))
        project_root = Path(self.cfg["project_root_path"])

        read_files = [item for item in payload.get("read_files", []) if str(item.get("file", "")).strip()]
        edit_files = [item for item in payload.get("edit_files", []) if str(item.get("file", "")).strip()]
        if not read_files:
            read_files = [{"file": "Core/Src/main.c", "why": "理解当前主流程。"}]
        if not edit_files and template.template_id.startswith("fallback_"):
            edit_files = [{"file": "Core/Src/main.c", "instructions": "做最小安全改动。"}]

        shell_steps = list(payload.get("shell_steps", [])) or _build_default_shell_steps()
        for item in shell_steps:
            if item.get("command") == "./agent_workbench.bat build --json" and item.get("on_failure"):
                item["on_failure"].setdefault("retry_command", "./agent_workbench.bat fix-build --json")

        related_files: list[str] = []
        for item in [*read_files, *edit_files]:
            file_path = str(item.get("file", "")).strip()
            if file_path and file_path not in related_files:
                related_files.append(file_path)

        hardware_context = self._build_hardware_context(template.template_id, params, snapshot)
        code_change_hints = self._build_code_change_hints(
            template.template_id,
            user_request,
            params,
            snapshot,
            hardware_context,
            edit_files,
        )
        notes = self._build_notes(template.template_id, params, snapshot, hardware_context)

        steps: list[dict[str, Any]] = []
        step_id = 1
        for item in read_files:
            steps.append(
                {
                    "id": step_id,
                    "name": str(item.get("name", f"读取 {item.get('file', '')}")),
                    "action_type": "read_file",
                    "file": item.get("file", ""),
                    "why": str(item.get("why", "为后续修改建立准确上下文。")),
                }
            )
            step_id += 1

        for item in edit_files:
            file_path = str(item.get("file", "")).strip()
            absolute_path = project_root / file_path
            steps.append(
                {
                    "id": step_id,
                    "name": str(item.get("name", f"修改 {file_path}")),
                    "action_type": "edit_file" if absolute_path.exists() else "create_file",
                    "file": file_path,
                    "instructions": str(item.get("instructions", "")),
                    "code_change_hints": code_change_hints.get(file_path, []),
                    "parameter_extractions": params.to_dict(),
                }
            )
            step_id += 1

        for item in shell_steps:
            shell_step = {
                "id": step_id,
                "name": str(item.get("name", "执行命令")),
                "action_type": "shell",
                "command": str(item.get("command", "")),
                "success_criteria": str(item.get("success_criteria", "exit_code == 0")),
            }
            if item.get("on_failure"):
                shell_step["on_failure"] = item["on_failure"]
            if item.get("requires_confirmation"):
                shell_step["requires_confirmation"] = True
            steps.append(shell_step)
            step_id += 1

        stable_strings = _normalize_stable_strings(
            list(payload.get("stable_strings", [])),
            [
                str(self.cfg["uart"].get("ready_banner", "")).strip(),
                str(self.cfg["uart"].get("prompt", "")).strip(),
            ],
        )

        return {
            "plan_id": f"plan_{local_now_tag()}",
            "user_request": user_request,
            "understanding": self._build_understanding(template.template_id, payload, params, hardware_context),
            "mode": str(payload.get("mode", "feature")),
            "template_id": template.template_id,
            "matched_keywords": matched_keywords,
            "parameter_extractions": params.to_dict(),
            "hardware_context": hardware_context,
            "notes": notes,
            "context": {
                "project": self.cfg["project"]["name"],
                "related_files": related_files,
                "available_cli_commands": snapshot.get("uart", {}).get("help_commands", []),
                "existing_peripherals": snapshot.get("detected_init_functions", []),
                "existing_handles": snapshot.get("existing_handles", []),
                "user_code_regions": snapshot.get("user_code_regions", []),
                "stable_strings_to_preserve": stable_strings,
            },
            "steps": steps,
            "final_report_template": {
                "required_fields": [
                    "修改的文件",
                    "编译结果",
                    "烧录结果",
                    "CLI 验证结果",
                    "证据路径",
                ]
            },
            "constraints": {
                "allowed_edit_files": [str(item.get("file", "")).strip() for item in edit_files if str(item.get("file", "")).strip()],
                "max_total_steps": int(self.cfg["planner"].get("max_total_steps", 15)),
                "forbidden_operations": payload.get(
                    "forbidden_operations",
                    [
                        "删除已有 CLI 命令",
                        "修改 ready banner 或 prompt 字符串",
                        "改动 Drivers 目录",
                    ],
                ),
            },
        }
