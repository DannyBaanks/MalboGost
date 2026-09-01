# gost -- Minimal Malbolge interpreter
# Build:  make          (default, gcc)
#         make msvc     (MSVC via cl)
#         make clean

CC      = gcc
CFLAGS  = -O2 -Wall -Wextra -std=c11
TARGET  = gost

.PHONY: all clean msvc test

all: $(TARGET)

$(TARGET): gost.c
	$(CC) $(CFLAGS) -o $@ $<

msvc:
	cl /O2 /W4 gost.c

clean:
	-del $(TARGET).exe 2>nul
	-del $(TARGET) 2>nul

# Quick smoke test: echo program
test: $(TARGET)
	@echo --- echo test ---
	@echo u | ./$(TARGET) examples/echo.mal
	@echo --- truth machine ---
	@echo 0 | ./$(TARGET) examples/truth.mal
	@echo 1 | ./$(TARGET) examples/truth.mal
