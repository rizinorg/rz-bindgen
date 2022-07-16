#include <iostream>

#define ABORT_IF(cond, msg)                                                    \
        if (cond) {                                                            \
                std::cout << msg << std::endl;                                 \
                return;                                                        \
        }
