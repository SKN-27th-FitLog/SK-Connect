import { useMemo, useState } from "react";
import { Alert } from "react-native";
import { validatePostForm } from "../utils/validators";
import { createPost } from "../api/postApi";

export default function useCreatePostForm(navigation) {
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [selectedCategory, setSelectedCategory] = useState("");
    const [location, setLocation] = useState("");
    const [imageUri, setImageUri] = useState("");

    const isFormValid = useMemo(() => {
        return !!title.trim() && !!content.trim() && !!selectedCategory.trim();
    }, [title, content, selectedCategory]);

    const handleSelectLocation = () => {
        Alert.alert("안내", "위치 선택 기능은 추후 API 연동 예정입니다.");
    };

    const handleSelectImage = () => {
        Alert.alert("안내", "이미지 선택 기능은 추후 API 연동 예정입니다.");
    };

    const handleSubmit = async () => {
        const error = validatePostForm({
        title,
        content,
        category: selectedCategory,
        });

        if (error) {
        Alert.alert("입력 확인", error);
        return;
        }

        try {
        await createPost({
            title,
            content,
            selectedCategory,
            imageUrls: imageUri ? [imageUri] : [],
        });

        Alert.alert("등록 완료", "게시글이 등록되었습니다.");

        navigation.navigate("PostList", {
            refresh: true, // [추가] 목록 다시 조회
        });
        } catch (error) {
        console.log("게시글 등록 실패:", error);
        Alert.alert(
            "등록 실패",
            error?.response?.data?.detail ||
            error?.message ||
            "게시글 등록 중 오류가 발생했습니다."
        );
        }
    };

    return {
        title,
        setTitle,
        content,
        setContent,
        selectedCategory,
        setSelectedCategory,
        location,
        setLocation,
        imageUri,
        setImageUri,
        isFormValid,
        handleSelectLocation,
        handleSelectImage,
        handleSubmit,
    };
    }