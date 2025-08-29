#include <vector>
#include <string>
#include <cmath>

#include <vector>
#include <string>

std::vector<std::string> func0(std::string input) {
    std::vector<std::string> result;
    std::string current;
    int depth = 0;
    
    for (size_t i = 0; i < input.length(); i++) {
        char c = input[i];
        
        if (c == '(') {
            depth++;
            current += c;
        } 
        else if (c == ')') {
            depth--;
            current += c;
            
            if (depth == 0) {
                result.push_back(current);
                current = "";
            }
        }
    }
    
    return result;
}

float fractional_part(float x) {
    int int_part = (int)x;          // Truncate to integer
    float float_part = (float)int_part;  // Convert back to float
    return x - float_part;          // Return fractional part
}

#include <vector>
#include <cmath>

bool func0(std::vector<float>& vec, float threshold) {
    for (int i = 0; i < vec.size(); i++) {
        for (int j = i + 1; j < vec.size(); j++) {
            float diff = vec[i] - vec[j];
            if (std::abs(diff) < threshold) {
                return true;
            }
        }
    }
    return false;
}

