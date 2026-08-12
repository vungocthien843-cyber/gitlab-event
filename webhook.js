import Pusher from 'pusher';

// Khởi tạo Pusher bằng Biến môi trường (Bảo mật)
const pusher = new Pusher({
  appId: process.env.PUSHER_APP_ID,
  key: process.env.PUSHER_KEY,
  secret: process.env.PUSHER_SECRET,
  cluster: process.env.PUSHER_CLUSTER,
  useTLS: true
});

export default async function handler(req, res) {
  // Chỉ nhận luồng dữ liệu POST từ GitHub bắn tới
  if (req.method === 'POST') {
    const payload = req.body;
    
    // Trích xuất thông tin từ GitHub
    const pusherName = payload.pusher?.name || 'Ẩn danh';
    const repoName = payload.repository?.name || 'Unknown Repo';
    const commitId = payload.after ? payload.after.substring(0, 7) : 'N/A';

    try {
      // Bắn dữ liệu lên Pusher
      await pusher.trigger('webhook-events', 'push_started', {
        id: commitId,
        status: 'processing',
        message: `Phát hiện ${pusherName} vừa push code lên ${repoName}!`
      });
      
      res.status(200).send('Đã phát sóng thành công');
    } catch (error) {
      console.error("Lỗi Pusher:", error);
      res.status(500).send('Lỗi hệ thống');
    }
  } else {
    res.status(405).send('Chỉ chấp nhận method POST');
  }
}