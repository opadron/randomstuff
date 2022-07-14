
#include <stdlib.h>
#include <stdio.h>

const char *OP_ADD      = "+"  ;
const char *OP_ADDE     = "+=" ;
#define OP_ADDR_OF OP_BAND
const char *OP_AND      = "&&" ;
const char *OP_ANDE     = "&&=";
const char *OP_ASSIGN   = "="  ;
const char *OP_BAND     = "&"  ;
const char *OP_BANDE    = "&=" ;
const char *OP_BOR      = "|"  ;
const char *OP_BORE     = "|=" ;
const char *OP_DEC      = "--" ;
#define OP_DEREF OP_MUL;
const char *OP_DIV      = "/"  ;
const char *OP_DIVE     = "/=" ;
const char *OP_EQUAL    = "==" ;
const char *OP_GREAT    = ">"  ;
const char *OP_GREATE   = ">=" ;
const char *OP_INC      = "++" ;
const char *OP_LESS     = "<"  ;
const char *OP_LESSE    = "<=" ;
const char *OP_LSHIFT   = "<<" ;
const char *OP_LSHIFTE  = "<<=";
const char *OP_MUL      = "*"  ;
const char *OP_MULE     = "*=" ;
const char *OP_OR       = "||" ;
const char *OP_ORE      = "||=";
const char *OP_POINT    = "->" ;
const char *OP_RSHIFT   = ">>" ;
const char *OP_RSHIFTE  = ">>=";
const char *OP_SUB      = "-"  ;
const char *OP_SUBE     = "-=" ;


#define TYPE_DECL(A) struct A; typedef struct A A
#define TYPE_DEF(A) struct A

TYPE_DECL(binary_op);
TYPE_DECL(expression);
TYPE_DECL(paren_expr);
TYPE_DECL(unary_op);

TYPE_DEF(unary_op) {
    unsigned char pre;
    char operator;
    expression *expr;
};

TYPE_DEF(binary_op) {
    char operator;
    expression *left;
    expression *right;
};

TYPE_DEF(paren_expr) {
};

TYPE_DECL(reference_counted);
TYPE_DEF(reference_counted) {
    size_t ref_count;
    void (*destructor)(void *);
};

static inline void *
init_ref(void *ths_, void (*destructor)(void *)) {
    reference_counted *ths = ths_;
    ths->ref_count = 0;
    ths->destructor = destructor;

    return ths_;
}

static inline void *
new_ref(void *ths_) {
    reference_counted *ths = ths_;
    ++ths->ref_count;
    return ths_;
}

static inline void
del_ref(void *ths_) {
    reference_counted *ths = ths_;
    --ths->ref_count;
    if (ths->ref_count == 0) {
        if (ths->destructor) {
            ths->destructor(ths_);
        }
        free(ths_);
    }
}

TYPE_DECL(vector);
TYPE_DEF(vector) {
    reference_counted _;
    unsigned char *buffer;
    size_t esize;
    size_t count;
    size_t cap;
    void (*element_destructor)(void *);
};

static inline void
del_vector(void *ths_) {
    vector *ths = ths_;
    void *p;

    void (*dest)(void *) = ths->element_destructor;

    if (dest) {
        for (p = ths->buffer; ths->count--; p += ths->esize) {
            dest(p);
        }
    }

    free(ths->buffer);
    free(ths_);
}

void
vector_reserve(vector *ths, size_t count) {
    size_t requested_size = ths->esize * count;

    if (requested_size > ths->cap) {
        ths->buffer = realloc(ths->buffer, requested_size);
    }
}

vector *
new_vector(size_t esize, size_t cap, void (*dest)(void *)) {
    vector *ths = init_ref(malloc(sizeof(*ths)), del_vector);
    ths->esize = esize;
    ths->cap = cap;
    ths->count = 0;
    ths->element_destructor = dest;
    ths->buffer = NULL;

    vector_reserve(ths, cap);
    return ths;
}

void *
vector_push(vector *ths) {
    void *result;
    vector_reserve(ths, ths->count + 1);
    result = ths->buffer + ths->esize*ths->count;
    ++ths->count;
    return result;
}

void *
vector_at(vector *ths, size_t index) {
    void *result = NULL;
    if (index < ths->count) {
        result = ths->buffer + ths->esize*index;
    }

    return result;
}

void
vector_iter(vector *ths, int (*iter_func)(void *, size_t)) {
    void *p = ths->buffer;
    size_t i;

    for (i = 0; i < ths->count; ++i) {
        if (iter_func(p, i)) {
            break;
        }
        p += ths->esize;
    }
}

TYPE_DECL(boxed_int);
TYPE_DEF(boxed_int) {
    reference_counted _;
    int value;
};

boxed_int *
mkint(int x) {
    boxed_int *ths = init_ref(malloc(sizeof(*ths)), NULL);
    ths->value = x;
    return ths;
}

int
print_int(void *ths_, size_t i) {
    boxed_int *ths = ths_;
    printf("%d\n", ths->value);
    return 0;
}

void
ptr_dest(void *ths_) {
    if (ths_) {
        ths_ = *(void **)ths_;
        if (ths_) {
            del_ref(ths_);
        }
    }
}

int
main(int argc, char **argv) {
    vector *v = new_ref(new_vector(sizeof(boxed_int *), 2, ptr_dest));
    boxed_int **p;

    p = vector_push(v); *p = new_ref(mkint(0));
    p = vector_push(v); *p = new_ref(mkint(1));
    p = vector_push(v); *p = new_ref(mkint(2));
    p = vector_push(v); *p = new_ref(mkint(3));

    p = vector_push(v); *p = new_ref(*(boxed_int **)vector_at(v, 2));
    p = vector_push(v); *p = new_ref(*(boxed_int **)vector_at(v, 1));
    p = vector_push(v); *p = new_ref(*(boxed_int **)vector_at(v, 0));

    vector_iter(v, print_int);

    del_ref(v);
}

