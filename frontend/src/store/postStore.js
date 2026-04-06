let posts = [];

export function getPosts() {
    return posts;
}

export function addPost(newPost) {
    posts = [newPost, ...posts];
}

export function updatePost(updatedPost) {
    posts = posts.map((post) =>
        post.id === updatedPost.id ? { ...post, ...updatedPost } : post
    );
}