import React from "react";
import { View, TouchableOpacity, Text } from "react-native";

export default function PostTabs({ tabs = [], activeTab, onChangeTab }) {
    return (
        <View style={{ flexDirection: "row", gap: 10 }}>
        {tabs.map((tab) => (
            <TouchableOpacity
            key={tab.key}
            onPress={() => onChangeTab(tab.key)}
            style={{
                paddingVertical: 10,
                paddingHorizontal: 14,
                borderRadius: 20,
                backgroundColor: activeTab === tab.key ? "#2c2c2c" : "#f1f1f1",
                justifyContent: "center",
                alignItems: "center",
            }}
            >
            <Text
                style={{
                fontSize: 14,
                fontWeight: "500",
                color: activeTab === tab.key ? "#fff" : "#222",
                }}
            >
                {tab.label}
            </Text>
            </TouchableOpacity>
        ))}
        </View>
    );
    }