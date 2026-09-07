#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _get_lan_ip():
    """Detect the machine's LAN IP via a lightweight UDP probe. No data sent."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def _get_port():
    """Parse the port from sys.argv, defaulting to 8000."""
    for arg in sys.argv:
        if arg == 'runserver' or arg.endswith('.py') or arg.startswith('-'):
            continue
        if ':' in arg:
            return arg.split(':')[-1]
        if arg.isdigit():
            return arg
    return '8000'


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kb_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    if 'runserver' in sys.argv:
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        port   = _get_port()
        lan_ip = _get_lan_ip()

        

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
