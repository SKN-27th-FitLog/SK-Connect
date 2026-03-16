import React from "react";
import { View, ScrollView, Text, TouchableOpacity } from "react-native";
import { postCreateStyles as styles } from "../styles/postStyles";
import useCreatePostForm from "../hooks/useCreatePostForm";
import PostFormFields from "../components/post/PostFormFields";

export default function PostCreateScreen({ navigation }) {
  const {
    title,
    setTitle,
    content,
    setContent,
    selectedCategory,
    setSelectedCategory,
    location,
    handleSelectLocation,
    handleSelectImage,
    handleSubmit,
    isFormValid,
  } = useCreatePostForm(navigation);

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.contentContainer}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.screenTitle}>게시글 작성</Text>

        <PostFormFields
          title={title}
          setTitle={setTitle}
          content={content}
          setContent={setContent}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          location={location}
          handleSelectLocation={handleSelectLocation}
          handleSelectImage={handleSelectImage}
        />
      </ScrollView>

      <View style={styles.bottomArea}>
        <TouchableOpacity
          style={[
            styles.submitButton,
            !isFormValid && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={!isFormValid}
        >
          <Text style={styles.submitButtonText}>등록하기</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}