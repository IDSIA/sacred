#include <unistd.h>
#include <errno.h>

#define BUFFER_SIZE 64


int main(int argc,  char** argv) {
    char buffer[BUFFER_SIZE];
    ssize_t len;

    while ((len = read(STDIN_FILENO, &buffer, sizeof(buffer))) > 0)
    {
        len = write(STDOUT_FILENO, &buffer, len);
        len = write(STDERR_FILENO, &buffer, len);
    }
    if (len != 0)
        return errno;
    return 0;
}
