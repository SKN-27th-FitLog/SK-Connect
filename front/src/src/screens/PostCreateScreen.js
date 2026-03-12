import React, { useMemo, useState } from "react";
import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Alert,
  ScrollView,
} from "react-native";
import { addPost } from "../store/postStore";
import { postCreateStyles as styles } from "../styles/postStyles";

const CATEGORY_OPTIONS = [
  { key: "study", label: "스터디" },
  { key: "exercise", label: "운동" },
  { key: "restaurant", label: "맛집" },
  { key: "hobby", label: "취미" },
  { key: "networking", label: "네트워킹" },
  { key: "etc", label: "기타" },
];

export default function PostCreateScreen({ navigation }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [location, setLocation] = useState("");
  const [imageUri, setImageUri] = useState("");
  

  const isFormValid = useMemo(() => {
    return (
      title.trim().length > 0 &&
      content.trim().length > 0 &&
      selectedCategory.trim().length > 0
    );
  }, [title, content, selectedCategory]);

  const handleSubmit = () => {
    if (!isFormValid) {
      Alert.alert("입력 확인", "제목, 내용, 카테고리는 필수 입력입니다.");
      return;
    }

    const today = new Date();
    const createdAt = `${today.getFullYear()}. ${today.getMonth() + 1}. ${today.getDate()}.`;

    const newPost = {
      id: Date.now().toString(),
      author: "익명",
      authorBadge: "익",
      createdAt,
      title: title.trim(),
      content: content.trim(),
      category:
        CATEGORY_OPTIONS.find((item) => item.key === selectedCategory)?.label || "",
      location: location.trim(),
      imageUrl: imageUri,
      likeCount: 0,
      commentCount: 0,
      liked: false,
      comments: [],
    };

    Alert.alert("등록 완료", "게시글이 등록되었습니다.", [
      {
        text: "확인",
        onPress: () => {
          addPost(newPost);
          navigation.navigate("MainTabs",{screen:"PostList",params:{newPost}});
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} activeOpacity={0.8}>
            <Text style={styles.backButton}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>게시글 작성</Text>
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.contentContainer}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.section}>
            <Text style={styles.label}>제목</Text>
            <TextInput
              value={title}
              onChangeText={setTitle}
              placeholder="제목을 입력하세요"
              placeholderTextColor="#9CA3AF"
              style={styles.input}
              maxLength={50}
            />
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>내용</Text>
            <TextInput
              value={content}
              onChangeText={setContent}
              placeholder="내용을 입력하세요"
              placeholderTextColor="#9CA3AF"
              style={[styles.input, styles.textArea]}
              multiline
              textAlignVertical="top"
              maxLength={1000}
            />
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>카테고리</Text>
            <View style={styles.categoryGrid}>
              {CATEGORY_OPTIONS.map((item) => {
                const isSelected = selectedCategory === item.key;

                return (
                  <TouchableOpacity
                    key={item.key}
                    style={[
                      styles.categoryButton,
                      isSelected && styles.categoryButtonSelected,
                    ]}
                    activeOpacity={0.85}
                    onPress={() => setSelectedCategory(item.key)}
                  >
                    <Text
                      style={[
                        styles.categoryButtonText,
                        isSelected && styles.categoryButtonTextSelected,
                      ]}
                    >
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>위치 (선택)</Text>
            <View style={styles.locationRow}>
              <View style={styles.locationInputWrapper}>
                <Text style={styles.locationIcon}>📍</Text>
                <TextInput
                  value={location}
                  onChangeText={setLocation}
                  placeholder="장소를 입력하세요 (예: 강남역, 홍대입구)"
                  placeholderTextColor="#9CA3AF"
                  style={styles.locationInput}
                />
              </View>

              <TouchableOpacity
                style={styles.searchButton}
                activeOpacity={0.85}
                onPress={() =>
                  Alert.alert("위치 검색", "위치 검색 기능은 아직 연결 전입니다.")
                }
              >
                <Text style={styles.searchButtonText}>⌕</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>이미지</Text>
            <TouchableOpacity
              style={styles.imageUploadBox}
              activeOpacity={0.85}
              onPress={() =>
                Alert.alert("이미지 추가", "이미지 추가 기능은 아직 연결 전입니다.")
              }
            >
              <Text style={styles.imageUploadIcon}>🖼️</Text>
              <Text style={styles.imageUploadText}>
                {imageUri ? "이미지 선택됨" : "추가"}
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>

        <View style={styles.bottomArea}>
          <TouchableOpacity
            style={[
              styles.submitButton,
              !isFormValid && styles.submitButtonDisabled,
            ]}
            activeOpacity={isFormValid ? 0.85 : 1}
            onPress={handleSubmit}
          >
            <Text style={styles.submitButtonText}>등록하기</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}
