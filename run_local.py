import socket
import subprocess
import sys

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    ip = get_local_ip()
    print("==================================================")
    print(f"🚀 STARTING KB FOUNDATION SERVER")
    print(f"🌍 THE SINGLE URL FOR ALL DEVICES (LAPTOP & PHONE) IS:")
    print(f"👉 http://{ip}:8000")
    print("==================================================")
    
    try:
        # This binds the server STRICTLY to the single IP address
        subprocess.run([sys.executable, "manage.py", "runserver", f"{ip}:8000"])
    except KeyboardInterrupt:
        print("\nServer stopped.")