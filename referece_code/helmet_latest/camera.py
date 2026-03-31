# camera.py

def get_cameras():
    """
    Returns a list of camera configurations including names, RTSP URLs, and detection thresholds.
    """
    return [
         {
            "camera": "CCTV NO. 118 MHAWK STORE 2",
            "cam_url": "rtsp://admin:mahindra%40123@10.5.12.161/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])  
        },
        {
            "camera": "CCTV NO. 114 NEW STRONG ROOM 1",
            "cam_url": "rtsp://admin:12345@10.5.12.101/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])  

        },
        {
            "camera": "CCTV NO. 115 NEW STRONG ROOM 2",
            "cam_url": "rtsp://admin:12345@10.5.12.102/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "CCTV NO. 116 NEW STRONG ROOM 3",
            "cam_url": "rtsp://admin:12345@10.5.12.103/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "CCTV NO. 117 MHAWK STORE 3",
            "cam_url": "rtsp://admin:123456@10.5.12.162/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.60,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "CCTV NO. 21 MDI STORE 2",
            "cam_url": "rtsp://root:admin123@10.5.12.164/live.sdp",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "CCTV NO. 22 MDI STORE 3",
            "cam_url": "rtsp://admin:123456@10.5.12.145/streaming/channels/101",
            "high_threshold": 0.50,
            "low_threshold": 0.90,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "CCTV NO. 23 OLD STRONG ROOM",
            "cam_url": "rtsp://root:admin@10.5.28.64/live.sdp",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "CCTV NO. 24 OLD STRONG ROOM TEM",
            "cam_url": "rtsp://admin:123456@10.5.28.63/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.80,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
        {
            "camera": "NEW PLANT",
            "cam_url": "rtsp://admin:mahindra%40123@10.5.28.145/streaming/channels/101",
            "high_threshold": 0.30,
            "low_threshold": 0.60,
            "roi": np.array([(200, 720), (600, 400), (900, 400), (1300, 720)])
        },
    ]
