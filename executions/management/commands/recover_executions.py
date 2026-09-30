from django.core.management.base import BaseCommand

from executions.engine import recover_interrupted_executions


class Command(BaseCommand):
    help = "Mark executions left RUNNING by a previous server process as STOPPED."

    def handle(self, *args, **options):
        count = recover_interrupted_executions()
        self.stdout.write(f"Recovered {count} interrupted execution(s)")
