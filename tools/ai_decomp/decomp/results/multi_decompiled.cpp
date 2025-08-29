#include <vector>
#include <string>

std::vector<std::string> func1(std::string str) {
    std::vector<std::string> result;
    std::string current;
    int balance = 0;
    
    for (int i = 0; i < str.length(); i++) {
        char c = str[i];
        
        if (c == '(') {
            balance++;
            current += c;
        } else if (c == ')') {
            balance--;
            current += c;
            
            if (balance == 0) {
                result.push_back(current);
                current = "";
            }
        } else {
            current += c;
        }
    }
    
    return result;
}

float func2(float x) {
    float fractional_part = x - (int)x;
    return fractional_part;
}

#include <vector>
#include <cmath>

bool func3(std::vector<float> vec, float threshold) {
    for (int i = 0; i < vec.size(); ++i) {
        for (int j = i + 1; j < vec.size(); ++j) {
            float diff = std::abs(vec[i] - vec[j]);
            if (diff < threshold) {
                return true;
            }
        }
    }
    return false;
}

