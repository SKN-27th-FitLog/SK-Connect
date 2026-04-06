import { addPost, getPosts, updatePost } from "../store/postStore";

export function fetchPosts() {
    return getPosts();
    }

    export function createPost(post) {
    return addPost(post);
    }

    export function savePost(post) {
    return updatePost(post);
    }