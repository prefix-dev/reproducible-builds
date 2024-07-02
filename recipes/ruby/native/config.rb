require 'mkmf';

# extension name
extname = 'hello';

# destination directory
dir_config(extname)

create_makefile(extname);
