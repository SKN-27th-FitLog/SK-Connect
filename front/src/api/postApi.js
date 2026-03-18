import axios from "axios";

const api = axios.create({
  baseURL: "http://10.0.2.2:8000",
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
    author: "익명",
    authorBadge: "익",
    createdAt: formatDate(item?.created_at),
    imageUrl: firstImage || "",
    likeCount: 0,
    commentCount: 0,
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
    likeCount: 0,
    liked: false,
    category: item?.category?.name ?? "",
    categoryCd: item?.post_cd ?? "",
    location: item?.map?.address_detail ?? "",
    comments: [],
    statusCd: item?.status_cd ?? "",
  };
};

export const fetchPostList = async () => {
  try {
    const response = await api.get("/posts/");
    console.log("게시글 목록 응답:", response.data);

    const list = Array.isArray(response.data) ? response.data : [];
    return list.map(mapListPost);
  } catch (err) {
    console.log("=== fetchPostList 에러 ===");
    console.log("message:", err.message);
    console.log("url:", err.config?.baseURL + err.config?.url);
    console.log("method:", err.config?.method);
    console.log("status:", err.response?.status);
    console.log("response:", err.response?.data);
    throw err;
  }
};

export const fetchPostDetail = async (postId) => {
  try {
    const response = await api.get(`/posts/${postId}/`);
    console.log("게시글 상세 응답:", response.data);
    return mapDetailPost(response.data);
  } catch (err) {
    console.log("=== fetchPostDetail 에러 ===");
    console.log("message:", err.message);
    console.log("url:", err.config?.baseURL + err.config?.url);
    console.log("method:", err.config?.method);
    console.log("status:", err.response?.status);
    console.log("response:", err.response?.data);
    throw err;
  }
};

export const createPost = async ({
  title,
  content,
  selectedCategory,

  imageUrl = ["https://example.com/default.jpg"],

}) => {
  const payload = {
    title: title ?? "",
    content: content ?? "",
    post_cd: selectedCategory ?? "",
    status_cd: "ST01",
    latitude: 0,
    longitude: 0,
    address_cd: "ADDR_DEFAULT",
    address_detail: "기본 위치",
    image_url: imageUrl[0],
  };


  try {
    console.log("create payload:", payload);

    const response = await api.post("/api/posts/", payload);
    console.log("게시글 생성 응답:", response.data);

    return response.data;
  } catch (err) {
    console.log("=== createPost 에러 ===");
    console.log("message:", err.message);
    console.log("url:", err.config?.baseURL + err.config?.url);
    console.log("method:", err.config?.method);
    console.log("data:", err.config?.data);
    console.log("status:", err.response?.status);
    console.log("response:", err.response?.data);
    throw err;
  }
};

export default {
  fetchPostList,
  fetchPostDetail,
  createPost,
};