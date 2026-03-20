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
      <View style={styles.header}>
        <TouchableOpacity 
          onPress={() => navigation.goBack()}
          style={{ flexDirection: 'row', alignItems: 'center', paddingRight: 20, paddingVertical: 10 }}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={styles.backButton}>‹</Text>
          <Text style={styles.headerTitle}>게시글 작성</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.contentContainer}
        showsVerticalScrollIndicator={false}
      >
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