#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/joystick.h>  // For struct js_event, etc.

int main(void) {
    // Open the joystick device
    int fd = open("/dev/input/js0", O_RDONLY);
    if (fd < 0) {
        perror("Could not open /dev/input/js0");
        return 1;
    }

    printf("Opened joystick at /dev/input/js0\n");
