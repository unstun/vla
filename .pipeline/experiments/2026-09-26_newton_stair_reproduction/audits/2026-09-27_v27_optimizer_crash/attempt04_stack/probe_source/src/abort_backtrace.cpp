// Diagnostic only: record the native call stack when the saved-input replay
// aborts or faults. GCC 11 prints libstdc++ assertion text with printf to
// buffered stdout, and abort() discards that buffer, so flush it first.
// Frames are symbolized afterwards with addr2line (gdb is absent in the image).
#include <execinfo.h>
#include <csignal>
#include <cstdio>
#include <unistd.h>

namespace {
void writeText(const char* text, size_t size) { (void)!write(STDERR_FILENO, text, size); }

void dumpStack(int signal_number) {
  std::fflush(stdout);
  const char header[] = "\n[CRASH-STACK-BEGIN]\n";
  writeText(header, sizeof(header) - 1);
  char line[48];
  const int length = std::snprintf(line, sizeof(line), "[CRASH-SIGNAL] %d\n", signal_number);
  if (length > 0) writeText(line, static_cast<size_t>(length));
  void* frames[128];
  const int count = backtrace(frames, 128);
  backtrace_symbols_fd(frames, count, STDERR_FILENO);
  const char footer[] = "[CRASH-STACK-END]\n";
  writeText(footer, sizeof(footer) - 1);
  std::signal(signal_number, SIG_DFL);
  std::raise(signal_number);
}

struct InstallHandlers {
  InstallHandlers() {
    void* warmup[1];
    backtrace(warmup, 1);  // Load the unwinder before any fault.
    std::signal(SIGABRT, dumpStack);
    std::signal(SIGSEGV, dumpStack);
  }
} install_handlers;
}  // namespace
