from dataclasses import dataclass, field
from pathlib import Path

import wandb

from ..classes.task import Task
from ..classes.template import Template
from ..config import const
from .base_manager import BaseManager
from .simulation_manager import SimulationManager


@dataclass
class TemplateManager(BaseManager):
    run_config: dict
    templates: dict[str, Template] = field(default_factory=dict)

    def load_templates(self) -> None:
        template_path = Path("data") / "templates"
        categories = [d.name for d in template_path.iterdir() if d.is_dir()]
        for category in categories:
            levels = [
                d.name
                for d in sorted((template_path / category).iterdir())
                if d.is_dir()
            ]
            for level in levels:
                self.templates[level] = Template(
                    id=level,
                    category=category,
                    run_config=self.run_config,
                )

    @property
    def template_ids(self) -> list[str]:
        return list(self.templates.keys())

    def get_templates_first_tasks(self, starting_level: str = "00000") -> list[Task]:
        return [
            level.get_first_task()
            for name, level in self.templates.items()
            if name >= starting_level
        ]

    def get_templates_tasks(
        self, limit: int, starting_level: str = "00000"
    ) -> list[Task]:
        tasks = []
        for level in self.templates.values():
            if level.id >= starting_level:
                tasks.extend(level.get_tasks(limit=limit))
        return tasks

    def get_tasks(self, limit: int, template_id: str) -> list[Task]:
        return self.templates[template_id].get_tasks(limit=limit)

    def iterate_templates(
        self,
        simulation_manager: SimulationManager,
        config_name: str,
        attempts_per_task: int,
        max_failures: int,
    ) -> None:
        tot_failures = 0
        tot_successes = 0
        tot_good_candidates = 0
        tot_bad_candidates = 0
        skipped_templates = 0

        for template_id in self.template_ids:
            template_failures = 0
            template_successes = 0
            template_good_candidates = 0
            template_bad_candidates = 0
            template_attempts = 0
            tasks = self.get_tasks(limit=attempts_per_task, template_id=template_id)
            for task in tasks:
                simulation_manager.load_task(task)
                (attempts, n_good_candidates, n_bad_candidates) = (
                    simulation_manager.find_proposals(
                        run_config_name=config_name, save_screenshots=True
                    )
                )
                template_good_candidates += n_good_candidates
                template_bad_candidates += n_bad_candidates
                template_attempts += attempts
                failed = attempts >= const.MAX_ATTEMPTS
                template_failures += 1 if failed else 0
                template_successes += 1 if not failed else 0
                if template_failures >= max_failures:
                    skipped_templates += 1
                    break

            tot_bad_candidates += template_bad_candidates
            tot_good_candidates += template_good_candidates
            tot_failures += template_failures
            tot_successes += template_successes
            wandb.log(
                {
                    "templates/n_failures": template_failures,
                    "templates/n_successes": template_successes,
                    "templates/good_candidates": template_good_candidates,
                    "templates/bad_candidates": template_bad_candidates,
                    "templates/attempts": template_attempts,
                }
            )

        wandb.log(
            {
                "total/n_failures": tot_failures,
                "total/n_successes": tot_successes,
                "total/skipped_tasks": simulation_manager.skipped_tasks,
                "total/skipped_templates": skipped_templates,
                "total/good_candidates": simulation_manager.total_good_candidates,
                "total/bad_candidates": simulation_manager.total_bad_candidates,
                "total/average_attempts": (
                    simulation_manager.total_attempts
                    / (len(self.template_ids) - skipped_templates)
                    if (len(self.template_ids) - skipped_templates) > 0
                    else 0
                ),
            }
        )
