#include <vector>
#include <string>

std::vector<std::string> func0(const std::string& str) {
    std::vector<std::string> result;
    std::string current;
    int balance = 0;
    
    for (int i = 0; i < str.length(); i++) {
        char c = str[i];
        
        if (c == '(') {
            balance++;
            current += c;
        } 
        else if (c == ')') {
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

float func0(float value) {
    return value - (int)value;
}

#include <vector>
#include <cmath>

bool func0(std::vector<float> vec, float threshold) {
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

