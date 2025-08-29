#include <vector>
#include <string>
#include <cmath>

// First overload: processes a string to extract balanced parentheses groups
std::vector<std::string> func0(const std::string& str) {
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
        }
    }
    
    return result;
}

// Second overload: returns the fractional part of a float
float func0(float x) {
    return x - static_cast<float>(static_cast<int>(x));
}

// Third overload: checks if any consecutive pair in vector has difference < threshold
bool func0(const std::vector<float>& vec, float threshold) {
    for (int i = 0; i < vec.size(); i++) {
        for (int j = i + 1; j < vec.size(); j++) {
            if (std::abs(vec[i] - vec[j]) < threshold) {
                return true;
            }
        }
    }
    return false;
}