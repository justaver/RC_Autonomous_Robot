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

    // We'll read events in a loop
    struct js_event e;
    while (1) {
        // read() will block until there's an event
        int bytesRead = read(fd, &e, sizeof(e));
        if (bytesRead < 0) {
            perror("Failed to read joystick event");
            break;
        }

        // e.type can have initialization bits, so we mask those out:
        unsigned int eventType = e.type & ~JS_EVENT_INIT;

        // Check if it's an axis or button event
        if (eventType == JS_EVENT_AXIS) {
            printf("AXIS %u VALUE %d\n", e.number, e.value);
        } else if (eventType == JS_EVENT_BUTTON) {
            printf("BUTTON %u VALUE %d\n", e.number, e.value);
        }
        else{
            printf("some other input");
        }
    }

    close(fd);
    return 0;
}
