import { useMemo, useState } from "react";
import { Alert } from "react-native";
import { validatePostForm } from "../utils/validators";
import { addPost } from "../store/postStore";

export default function usePostCreateForm(navigation) {
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

    const handleSubmit = () => {
        const error = validatePostForm({
        title,
        content,
        category: selectedCategory,
        });

        if (error) {
        Alert.alert("입력 확인", error);
        return;
        }

        const newPost = {
        id: Date.now().toString(),
        title,
        content,
        category: selectedCategory,
        location,
        imageUrl: imageUri,
        author: "익명",
        createdAt: new Date().toISOString(),
        likeCount: 0,
        commentCount: 0,
        comments: [],
        liked: false,
        };

        addPost(newPost);

        navigation.navigate("PostList", { newPost });
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