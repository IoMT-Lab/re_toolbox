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