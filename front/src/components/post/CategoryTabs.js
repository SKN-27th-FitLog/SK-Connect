import React from "react";
import { ScrollView, TouchableOpacity, Text } from "react-native";

export default function CategoryTabs({
    categories = [],
    selectedCategory,
    onSelectCategory,
    }) {
    return (
        <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{
            paddingHorizontal: 16,
            paddingVertical: 10,
            gap: 8,
        }}
        >
        {categories.map((category) => (
            <TouchableOpacity
            key={category.value} // 🔥 key도 value 기준
            onPress={() => onSelectCategory(category.value)} // 🔥 핵심
            style={{
                paddingVertical: 8,
                paddingHorizontal: 14,
                borderRadius: 18,
                backgroundColor:
                selectedCategory === category.value ? "#ff5a1f" : "#f3f3f3",
                borderWidth: selectedCategory === category.value ? 0 : 1,
                borderColor: "#e4e4e4",
            }}
            >
            <Text
                style={{
                fontSize: 13,
                fontWeight: "500",
                color: selectedCategory === category.value ? "#fff" : "#333",
                }}
            >
                {category.label}
            </Text>
            </TouchableOpacity>
        ))}
        </ScrollView>
    );
}