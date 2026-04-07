struct Point {
    int x;
    int y;
};

struct Stats {
    struct Point point;
    float weight;
    bool active;
};

struct Point make_point(int x, int y) {
    struct Point p;
    p.x = x;
    p.y = y;
    return p;
}

float scale_sum(struct Point p, float factor) {
    return (p.x + p.y) * factor;
}

int sum_array(int* values, int count) {
    int total = 0;
    int i = 0;

    for (i = 0; i < count; i = i + 1) {
        total = total + *(values + i);
    }

    return total;
}

float main() {
    int values[4];
    struct Stats stats;
    struct Stats* stats_ptr = &stats;
    struct Point copy;
    int total = 0;
    int i = 0;
    float result = 0.0;

    values[0] = 2;
    values[1] = 4;
    values[2] = 6;
    values[3] = 8;

    stats.point = make_point(3, 5);
    stats.weight = 1.5;
    stats.active = true;

    // Demonstrate pointer-based field access.
    stats_ptr->point.x = stats_ptr->point.x + 1;

    // Demonstrate whole-struct copy.
    copy = stats.point;

    total = sum_array(&values[0], 4);
    result = scale_sum(copy, stats.weight);

    // Demonstrate while/break/continue and boolean conditions.
    while (true) {
        if (!stats.active) {
            break;
        }

        result = result + total;

        for (i = 0; i < 4; i = i + 1) {
            if ((i % 2) == 0) {
                continue;
            }
            result = result + (values[i] / 2.0);
        }

        stats.active = false;
    }

    // Demonstrate float arithmetic and exponentiation.
    result = result + (2.0 ^ 3.0);

    return result;
}
