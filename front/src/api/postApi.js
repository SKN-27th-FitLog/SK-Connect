import axios from "axios";

const api = axios.create({
  // [변경 필요] 실행 환경에 맞게 수정
  // Android Emulator: http://10.0.2.2:8000
  // iOS Simulator: http://127.0.0.1:8000
  // 실기기: http://내PC아이피:8000
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

const formatDate = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}. ${date.getMonth() + 1}. ${date.getDate()}.`;
};

const mapListPost = (item) => {
  const firstImage =
    Array.isArray(item?.image) && item.image.length > 0
      ? item.image[0]?.image_url
      : "";

  return {
    id: item?.id?.toString?.() ?? "",
    title: item?.title ?? "",
    content: item?.content ?? "",
    author: "익명", // [주석] 현재 목록 API에는 작성자 정보 없음
    authorBadge: "익",
    createdAt: formatDate(item?.created_at),
    imageUrl: firstImage || "",
    likeCount: 0, // [주석] 현재 목록 API에는 없음
    commentCount: 0, // [주석] 현재 목록 API에는 없음
    liked: false,
    category: item?.cd_table?.name ?? "",
    categoryCd: item?.post_cd ?? "",
    location: item?.map?.address_detail ?? "",
    comments: [],
  };
};

const mapDetailPost = (item) => {
  const firstImage =
    Array.isArray(item?.image) && item.image.length > 0
      ? item.image[0]?.image_url
      : "";

  return {
    id: item?.id?.toString?.() ?? "",
    title: item?.title ?? "",
    content: item?.content ?? "",
    author: item?.user?.user_id ?? "익명",
    authorBadge: (item?.user?.user_id ?? "익명")?.[0] ?? "익",
    createdAt: formatDate(item?.created_at),
    imageUrl: firstImage || "",
    likeCount: 0, // [주석] 현재 상세 API에는 없음
    liked: false, // [주석] 현재 상세 API에는 없음
    category: item?.category?.name ?? "",
    categoryCd: item?.post_cd ?? "",
    location: item?.map?.address_detail ?? "",
    comments: [], // [주석] 현재 상세 API에는 없음
    statusCd: item?.status_cd ?? "",
  };
};

export const fetchPostList = async () => {
  const response = await api.get("/posts/");
  const list = Array.isArray(response.data) ? response.data : [];
  return list.map(mapListPost);
};

export const fetchPostDetail = async (postId) => {
  const response = await api.get(`/posts/${postId}/`);
  return mapDetailPost(response.data);
};

export const createPost = async ({
  title,
  content,
  selectedCategory,
  imageUrls = [],
}) => {
  const payload = {
    title: title ?? "",
    content: content ?? "",
    post_cd: selectedCategory ?? "",

    // [주석] map 기능 미완료라 임시 기본값
    status_cd: "STATUS_DEFAULT",
    latitude: 0,
    longitude: 0,
    address_cd: "ADDR_DEFAULT",
    address_detail: "",

    image_url: Array.isArray(imageUrls) ? imageUrls : [],
  };

  const response = await api.post("/posts/create/", payload);
  return response.data;
};

export default {
  fetchPostList,
  fetchPostDetail,
  createPost,
};