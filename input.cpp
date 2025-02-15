// Global declarations
int globalVar = 42;
bool globalFlag = false;

// A helper function that adds two integers.
int add(int x, int y) {
    return x + y;
}

int sub(int x, int y) {
    return x - y;
}

int main() {
    
    // Local variable declarations
    int a = 5;
    int b = 10;
    bool flag = true;
    
    // Function call and arithmetic
    int c = add(a, b);   // c = a + b
    int d = sub(a,b); // d = a - b
    int e = a % b; // e = a % b

    // Conditional using relational and logical operators
    if (flag && (c > 10)) {
        a = a + 1;
    } else {
        a = a - 1;
    }
    
    // Loop: increment 'a' until it is no longer less than 'c'
    while (a < c) {
        a = a + 2;
    }
    
    // Return the final value of a.
    return a;

}
