/* gost.c -- Minimal Malbolge interpreter.
 *
 * "gost" = the ghost in the machine.  A self-contained C implementation of the
 * Malbolge virtual machine, designed for three use cases:
 *
 *   1. Standalone CLI:   gost <file.mal> [max_steps] < input
 *   2. Library:          #include "gost.h" + link gost.c
 *   3. IPC mode:         gost --ipc  (JSONL on stdin/stdout, same protocol
 *                         as malbolge-ipc)
 *
 * Architecture:
 *   - 59049 trinary cells (3^10), each 0..59048
 *   - Overlay map for source cells + writes (linear scan, small programs)
 *   - Lazy crazy-chain fill for uninitialized cells
 *   - 7 real opcodes out of 94 decoded values
 *   - Post-step encryption via fixed substitution table
 *
 * Reference: Malbolge spec by Ben Olmstead (2000),
 *            implementation verified against malbolge-oracle (Python).
 *
 * Build:  gcc -O2 -o gost gost.c
 *         cl /O2 gost.c           (MSVC)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* ── constants ─────────────────────────────────────────────────────────── */

#define MEM_SIZE    59049u        /* 3^10                                  */
#define LAST        (MEM_SIZE-1)
#define HALF        243u          /* 3^5 — half-cell for crazy5            */
#define POW9        19683u        /* 3^9 — rotate multiplier               */
#define MAX_PROG    200000u       /* max source length                     */
#define MAX_OVERLAY 200000u       /* overlay capacity                      */
#define DEF_STEPS   100000000u    /* default step limit                    */

/* ── crazy operation ───────────────────────────────────────────────────── */

static const unsigned char CRAZY_T[3][3] = {
    {1, 0, 0},
    {1, 0, 2},
    {2, 2, 1}
};

static unsigned int crazy5[HALF][HALF];   /* precomputed 5-trit crazy */

static void crazy_init(void) {
    for (unsigned a = 0; a < HALF; a++) {
        for (unsigned b = 0; b < HALF; b++) {
            unsigned r = 0, p = 1, aa = a, bb = b;
            for (int k = 0; k < 5; k++) {
                r += CRAZY_T[bb % 3][aa % 3] * p;
                aa /= 3; bb /= 3; p *= 3;
            }
            crazy5[a][b] = r;
        }
    }
}

static unsigned int crazy(unsigned int a, unsigned int b) {
    return crazy5[a % HALF][b % HALF] + HALF * crazy5[a / HALF][b / HALF];
}

/* ── rotate ────────────────────────────────────────────────────────────── */

static unsigned int rotr(unsigned int n) {
    return POW9 * (n % 3) + n / 3;
}

/* ── xlat tables (standard Malbolge) ──────────────────────────────────── */

/* xlat1: decrypt -- index = (mem[c] - 33 + c) % 94 */
static const char XLAT1[95] =
    "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z'"
    ";FNQuY]szf$!BS/|t:Pn6^Ha";

/* xlat2: encrypt -- applied to mem[c] after execution */
static const char XLAT2[95] =
    "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|"
    "jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

/* ── memory: overlay + lazy chain ──────────────────────────────────────── */

static unsigned int ovl_addr[MAX_OVERLAY];
static unsigned int ovl_val[MAX_OVERLAY];
static unsigned int ovl_len;

static unsigned int chain[MEM_SIZE];
static unsigned int fill_start;    /* source ends here; chain starts here */
static unsigned int chain_until;   /* chain computed up to here           */

static unsigned int mem_get(unsigned int x) {
    /* overlay search */
    for (unsigned i = 0; i < ovl_len; i++)
        if (ovl_addr[i] == x) return ovl_val[i];
    /* below source = zero */
    if (x < fill_start) return 0;
    /* lazy fill */
    if (x >= chain_until) {
        unsigned end = ((x / HALF) + 1) * HALF;
        if (end > MEM_SIZE) end = MEM_SIZE;
        unsigned p1, p2;
        if (chain_until == fill_start) {
            p1 = (fill_start > 0) ? mem_get(fill_start - 1) : 0;
            p2 = (fill_start > 1) ? mem_get(fill_start - 2) : 0;
        } else {
            p1 = chain[chain_until - 1];
            p2 = chain[chain_until - 2];
        }
        for (unsigned i = chain_until; i < end; i++) {
            chain[i] = crazy(p1, p2);
            p2 = p1; p1 = chain[i];
        }
        chain_until = end;
    }
    return chain[x];
}

static void mem_set(unsigned int x, unsigned int v) {
    for (unsigned i = 0; i < ovl_len; i++) {
        if (ovl_addr[i] == x) { ovl_val[i] = v; return; }
    }
    if (ovl_len < MAX_OVERLAY) {
        ovl_addr[ovl_len] = x;
        ovl_val[ovl_len] = v;
        ovl_len++;
    }
}

static void mem_reset(void) {
    ovl_len = 0;
    chain_until = 0;
    fill_start = 0;
}

/* ── VM run ────────────────────────────────────────────────────────────── */

typedef struct {
    unsigned int  steps;
    int           terminated;
    char         *output;
    unsigned int  out_len;
    unsigned int  out_cap;
} RunResult;

static RunResult vm_run(const unsigned int *cells, unsigned int ncells,
                        const unsigned char *input, unsigned int input_len,
                        unsigned int max_steps) {
    RunResult r = {0, 0, NULL, 0, 65536};
    r.output = (char *)malloc(r.out_cap);
    if (!r.output) { r.out_cap = 0; return r; }

    mem_reset();
    fill_start = ncells > 2 ? ncells : 2;
    chain_until = fill_start;
    for (unsigned i = 0; i < ncells; i++) mem_set(i, cells[i]);

    unsigned int a = 0, c = 0, d = 0;
    unsigned int ipos = 0;

    for (unsigned step = 0; step < max_steps; step++) {
        unsigned ins = mem_get(c);
        if (ins < 33 || ins > 126) break;  /* invalid = crash */

        unsigned idx = (ins - 33 + c) % 94;
        char ix = XLAT1[idx];

        switch (ix) {
        case 'j': d = mem_get(d); break;                         /* d = [d]  */
        case '<': /* out a */
            if (r.out_len >= r.out_cap) {
                r.out_cap *= 2;
                r.output = (char *)realloc(r.output, r.out_cap);
            }
            r.output[r.out_len++] = (char)(a & 0xFF);
            break;
        case '/': /* in a */
            a = (ipos < input_len) ? input[ipos++] : 59048u;
            break;
        case '*': { /* rotr [d] */
            unsigned rv = rotr(mem_get(d));
            mem_set(d, rv); a = rv;
            break;
        }
        case 'i': c = mem_get(d); break;                         /* jmp [d]  */
        case 'p': { /* crz a,[d] */
            unsigned rv = crazy(a, mem_get(d));
            mem_set(d, rv); a = rv;
            break;
        }
        case 'v': r.terminated = 1; r.steps = step + 1;         /* halt     */
            return r;
        default: break;                                         /* nop      */
        }

        /* post-step: encrypt with xlat2, advance c and d */
        unsigned enc = mem_get(c);
        if (enc >= 33 && enc <= 126) mem_set(c, (unsigned)XLAT2[enc - 33]);
        c = (c == LAST) ? 0 : c + 1;
        d = (d == LAST) ? 0 : d + 1;
    }
    r.steps = max_steps;
    return r;
}

/* ── source loader ─────────────────────────────────────────────────────── */

static int load_source(const char *path, unsigned int *cells, unsigned int *ncells) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "gost: cannot open %s\n", path); return -1; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if ((unsigned long)sz > MAX_PROG) { fclose(f); fprintf(stderr, "gost: file too large\n"); return -1; }

    char buf[MAX_PROG];
    size_t n = fread(buf, 1, sz, f);
    fclose(f);

    unsigned count = 0;
    for (size_t i = 0; i < n; i++) {
        unsigned char ch = (unsigned char)buf[i];
        if (ch == 10 || ch == 13 || ch == 32 || ch == 9) continue;  /* skip ws */
        if (ch < 33 || ch > 126) {
            fprintf(stderr, "gost: invalid char %u at offset %zu\n", ch, i);
            return -1;
        }
        cells[count++] = ch;
    }
    *ncells = count;
    return 0;
}

/* ── stdin reader ──────────────────────────────────────────────────────── */

static unsigned char *read_stdin(unsigned int *len) {
    unsigned cap = 4096;
    unsigned char *buf = (unsigned char *)malloc(cap);
    unsigned n = 0;
    int ch;
    while ((ch = fgetc(stdin)) != EOF) {
        if (n >= cap) { cap *= 2; buf = (unsigned char *)realloc(buf, cap); }
        buf[n++] = (unsigned char)ch;
    }
    *len = n;
    return buf;
}

/* ── IPC mode (JSONL) ──────────────────────────────────────────────────── */

/* Minimal JSON helpers */
static char *json_find(char *s, const char *key) {
    char q[128];
    snprintf(q, sizeof(q), "\"%s\"", key);
    return strstr(s, q);
}

static char *json_string(char *s, char **end) {
    while (*s && *s != '"') s++;
    if (!*s) return NULL;
    s++;  /* skip opening " */
    char *start = s;
    while (*s && *s != '"') {
        if (*s == '\\') s++;  /* skip escaped char */
        s++;
    }
    if (*end) *end = s;
    return start;
}

static long json_long(char *s) {
    while (*s && !isdigit(*s) && *s != '-') s++;
    return strtol(s, NULL, 10);
}

static void ipc_loop(void) {
    /* seed crazy table (already done in main, but be safe) */
    puts("{\"status\":\"ready\"}");
    fflush(stdout);

    char line[1048576];
    while (fgets(line, sizeof(line), stdin)) {
        /* op */
        char *p = json_find(line, "op");
        if (!p) continue;
        char *op = json_string(p + 4, NULL);

        if (op && strcmp(op, "ping") == 0) {
            puts("{\"status\":\"OK\",\"output\":\"pong\"}");
            fflush(stdout);
            continue;
        }
        if (op && strcmp(op, "quit") == 0) break;

        if (op && strcmp(op, "run") == 0) {
            /* program */
            char *pp = json_find(line, "program");
            if (!pp) { puts("{\"status\":\"ERROR\",\"output\":\"no program\"}"); fflush(stdout); continue; }
            char *prog = json_string(pp + 10, NULL);

            /* steps (optional) */
            unsigned max_steps = DEF_STEPS;
            char *sp = json_find(line, "steps");
            if (sp) max_steps = (unsigned)json_long(sp + 7);

            /* input (optional) */
            char *inp = NULL;
            unsigned inplen = 0;
            char *ip = json_find(line, "input");
            if (ip) {
                inp = json_string(ip + 7, NULL);
                if (inp) inplen = strlen(inp);
            }

            /* load program */
            unsigned cells[MAX_PROG];
            unsigned ncells = 0;
            for (char *s = prog; *s && *s != '"'; s++) {
                unsigned char ch = (unsigned char)*s;
                if (ch == 10 || ch == 13 || ch == 32 || ch == 9) continue;
                if (ch < 33 || ch > 126) continue;
                cells[ncells++] = ch;
            }

            RunResult r = vm_run(cells, ncells,
                                 (const unsigned char *)inp, inplen,
                                 max_steps);

            /* output as JSON */
            printf("{\"status\":\"%s\",\"steps\":%u,\"output\":\"",
                   r.terminated ? "OK" : "TIMEOUT", r.steps);
            for (unsigned i = 0; i < r.out_len; i++) {
                unsigned char ch = (unsigned char)r.output[i];
                if (ch == '"') printf("\\\"");
                else if (ch == '\\') printf("\\\\");
                else if (ch == '\n') printf("\\n");
                else if (ch == '\r') printf("\\r");
                else if (ch == '\t') printf("\\t");
                else if (ch < 32) printf("\\u%04x", ch);
                else putchar(ch);
            }
            puts("\"}");
            fflush(stdout);
            free(r.output);
            continue;
        }

        /* unknown op */
        puts("{\"status\":\"ERROR\",\"output\":\"unknown op\"}");
        fflush(stdout);
    }
}

/* ── main ──────────────────────────────────────────────────────────────── */

int main(int argc, char **argv) {
    crazy_init();

    /* IPC mode */
    if (argc > 1 && strcmp(argv[1], "--ipc") == 0) {
        ipc_loop();
        return 0;
    }

    /* CLI mode: gost <file.mal> [max_steps] */
    if (argc < 2) {
        fprintf(stderr,
            "usage: gost <program.mal> [max_steps] < input\n"
            "       gost --ipc    (JSONL server mode)\n");
        return 1;
    }

    unsigned max_steps = DEF_STEPS;
    if (argc > 2) max_steps = (unsigned)atol(argv[2]);

    unsigned cells[MAX_PROG];
    unsigned ncells = 0;
    if (load_source(argv[1], cells, &ncells) < 0) return 2;
    if (ncells == 0) { fprintf(stderr, "gost: empty program\n"); return 2; }

    unsigned inplen = 0;
    unsigned char *input = read_stdin(&inplen);

    RunResult r = vm_run(cells, ncells, input, inplen, max_steps);

    /* write output to stdout */
    fwrite(r.output, 1, r.out_len, stdout);
    if (r.out_len > 0 && r.output[r.out_len - 1] != '\n') putchar('\n');

    /* stats to stderr */
    fprintf(stderr, "steps=%u output=%u terminated=%s\n",
            r.steps, r.out_len, r.terminated ? "yes" : "no (timeout)");

    free(r.output);
    free(input);
    return r.terminated ? 0 : 3;
}
