#include <ruby.h>
VALUE hello(VALUE self);

void Init_hello() {
  rb_define_global_function("hello", hello, 0);
}

VALUE hello(VALUE self)
{
  printf("Hello!\n");

  return Qnil;
}
