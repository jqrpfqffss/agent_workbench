import subprocess

script = "init\nreset run\nsleep 1000\nhalt\nmdw 0x200001b0 1\nresume\nsleep 1000\nhalt\nmdw 0x200001b0 1\nshutdown\n"
proc = subprocess.Popen(
    ["openocd", "-f", "interface/stlink.cfg", "-f", "target/stm32f1x.cfg"],
    cwd=r"h:\stm32_RAG\code\serial",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
out, _ = proc.communicate(script, timeout=10)
print(out)
print("returncode", proc.returncode)
