import React from "react";
import { View, Text, TextInput, TouchableOpacity } from "react-native";
import { CATEGORY_OPTIONS } from "../../constants/PostTabs";
import { postCreateStyles as styles } from "../../styles/postStyles";

export default function PostFormFields({
    title,
    setTitle,
    content,
    setContent,
    selectedCategory,
    setSelectedCategory,
    location,
    handleSelectLocation,
    handleSelectImage,
    }) {
    return (
        <View>
        <View style={styles.section}>
            <Text style={styles.label}>제목</Text>
            <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="제목을 입력하세요"
            placeholderTextColor="#9CA3AF"
            style={styles.input}
            />
        </View>

        <View style={styles.section}>
            <Text style={styles.label}>내용</Text>
            <TextInput
            value={content}
            onChangeText={setContent}
            placeholder="내용을 입력하세요"
            placeholderTextColor="#9CA3AF"
            multiline
            textAlignVertical="top"
            style={[styles.input, styles.textArea]}
            />
        </View>

        <View style={styles.section}>
            <Text style={styles.label}>카테고리</Text>
            <View style={styles.categoryGrid}>
            {(CATEGORY_OPTIONS ?? [])
                .filter((item) => item.value !== "ALL")
                .map((category) => {
                const selected =
                    selectedCategory?.value === category.value;

                return (
                    <TouchableOpacity
                    key={category.value}
                    onPress={() => setSelectedCategory(category)}
                    style={[
                        styles.categoryButton,
                        selected && styles.categoryButtonSelected,
                    ]}
                    >
                    <Text
                        style={[
                        styles.categoryButtonText,
                        selected && styles.categoryButtonTextSelected,
                        ]}
                    >
                        {category.label}
                    </Text>
                    </TouchableOpacity>
                );
                })}
            </View>
        </View>

        <View style={styles.section}>
            <Text style={styles.label}>위치</Text>
            <View style={styles.locationRow}>
            <TouchableOpacity
                onPress={handleSelectLocation}
                style={styles.locationInputWrapper}
            >
                <Text style={styles.locationIcon}>📍</Text>
                <Text style={styles.locationInput}>
                {location || "위치를 선택해주세요"}
                </Text>
            </TouchableOpacity>

            <TouchableOpacity
                onPress={handleSelectLocation}
                style={styles.searchButton}
            >
                <Text style={styles.searchButtonText}>⌕</Text>
            </TouchableOpacity>
            </View>
        </View>

        <View style={styles.section}>
            <Text style={styles.label}>이미지</Text>
            <TouchableOpacity
            onPress={handleSelectImage}
            style={styles.imageUploadBox}
            >
            <Text style={styles.imageUploadIcon}>＋</Text>
            <Text style={styles.imageUploadText}>이미지 추가</Text>
            </TouchableOpacity>
        </View>
        </View>
    );
}