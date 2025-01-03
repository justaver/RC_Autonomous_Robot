#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#define GPIO_BASE 0x3F200000 // GPIO base for Raspberry Pi 3/4
#define BLOCK_SIZE (4 * 1024)

volatile unsigned int *gpio;

void setup_gpio() {
    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) {
        perror("Unable to open /dev/mem");
        exit(EXIT_FAILURE);
    }
    gpio = mmap(NULL, BLOCK_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, GPIO_BASE);
    if (gpio == MAP_FAILED) {
        perror("Memory mapping failed");
        exit(EXIT_FAILURE);
    }
    close(mem_fd);
}

void set_gpio_output(int pin) {
    *(gpio + (pin / 10)) |= (1 << ((pin % 10) * 3));
}

void gpio_set(int pin) {
    *(gpio + 7) = (1 << pin);
}

void gpio_clear(int pin) {
    *(gpio + 10) = (1 << pin);
}

int main() {
    setup_gpio();
    int led_pin = 17; // GPIO17
    set_gpio_output(led_pin);

    while (1) {
        gpio_set(led_pin);
        sleep(1);
        gpio_clear(led_pin);
        sleep(1);
    }

    return 0;
}
