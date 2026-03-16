import React from "react";
import { ScrollView, TouchableOpacity, Text, View } from "react-native";

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
            key={category.key}
            onPress={() => onSelectCategory(category.key)}
            style={{
                paddingVertical: 8,
                paddingHorizontal: 14,
                borderRadius: 18,
                backgroundColor:
                selectedCategory === category.key ? "#ff5a1f" : "#f3f3f3",
                borderWidth: selectedCategory === category.key ? 0 : 1,
                borderColor: "#e4e4e4",
            }}
            >
            <Text
                style={{
                fontSize: 13,
                fontWeight: "500",
                color: selectedCategory === category.key ? "#fff" : "#333",
                }}
            >
                {category.label}
            </Text>
            </TouchableOpacity>
        ))}
        </ScrollView>
    );
    }