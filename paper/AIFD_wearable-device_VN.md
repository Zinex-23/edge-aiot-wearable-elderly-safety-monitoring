# CareFall: Phát hiện Té ngã Tự động thông qua Thiết bị đeo và các Phương pháp AI

**Tác giả:** Juan Carlos Ruiz-Garcia, Ruben Tolosana, Ruben Vera-Rodriguez, Carlos Moro
**Đơn vị:** Đại học Tự hành Madrid (Universidad Autonoma de Madrid), Tây Ban Nha; Cartronic Group, Tây Ban Nha.
**Email:** {juanc.ruiz, ruben.tolosana, ruben.vera}@uam.es; cmoro@cartronic.es

---

## TÓM TẮT (ABSTRACT)
Sự già hóa dân số đã dẫn đến số lượng các vụ té ngã ngày càng tăng trong xã hội, ảnh hưởng đến sức khỏe cộng đồng trên toàn thế giới. Bài báo này giới thiệu **CareFall**, một hệ thống phát hiện té ngã tự động (FDS) dựa trên các thiết bị đeo và các phương pháp Trí tuệ Nhân tạo (AI). CareFall xem xét các tín hiệu thời gian từ gia tốc kế (accelerometer) và con quay hồi chuyển (gyroscope) được trích xuất từ một chiếc đồng hồ thông minh (smartwatch). Hai phương pháp tiếp cận khác nhau được sử dụng để trích xuất đặc trưng và phân loại: i) dựa trên ngưỡng (threshold-based), và ii) dựa trên học máy (machine learning-based). Kết quả thực nghiệm trên hai cơ sở dữ liệu công khai cho thấy phương pháp dựa trên học máy - kết hợp thông tin từ cả gia tốc kế và con quay hồi chuyển - vượt trội hơn so với phương pháp dựa trên ngưỡng về độ chính xác (accuracy), độ nhạy (sensitivity) và độ đặc hiệu (specificity). Nghiên cứu này đóng góp vào việc thiết kế các giải pháp thông minh và thân thiện với người dùng nhằm giảm thiểu các hậu quả tiêu cực của việc té ngã ở người cao tuổi.

---

## 1. GIỚI THIỆU (INTRODUCTION)
Sự già hóa dân số đang gia tăng trên toàn thế giới. Tổ chức Y tế Thế giới (WHO) coi té ngã ở người cao tuổi là một thách thức lớn đối với sức khỏe cộng đồng toàn cầu [20]. Trên thực tế, té ngã có thể ảnh hưởng tiêu cực đến chất lượng cuộc sống của người cao tuổi, gây ra các hậu quả nghiêm trọng về thể chất, tâm lý và xã hội, chẳng hạn như bầm tím, gãy xương, chấn thương, tổn thương vận động và thần kinh, hoặc thậm chí tử vong [2, 7, 25]. Vì lý do này, việc thiết kế và triển khai các công nghệ thân thiện với người dùng để phát hiện té ngã là vô cùng quan trọng.

Trong những năm gần đây, các giải pháp như Hệ thống Đáp ứng Khẩn cấp Cá nhân (PERS) đã được đề xuất [3]. PERS là một hệ thống thủ công, theo đó một người sau khi ngã xuống đất phải nhấn nút cảnh báo (thường ở trong dây chuyền hoặc vòng tay), và một đội cấp cứu sẽ được cử đến ngay lập tức để hỗ trợ. Tuy nhiên, hệ thống này có thể không phải là một giải pháp tốt trong một số trường hợp, ví dụ như nếu người đó bị ngất hoặc mất ý thức do cú ngã và không thể nhấn nút khẩn cấp.

Để khắc phục các hạn chế của PERS, nhiều loại Hệ thống Phát hiện Té ngã (FDS) đã được đề xuất trong thập kỷ qua, cung cấp các giải pháp tự động và thân thiện với người cao tuổi [7, 21]. Hầu hết các FDS dựa trên các thiết bị đeo [22], chẳng hạn như thắt lưng hoặc vòng tay tích hợp cảm biến gia tốc [16, 17, 24], các thiết bị dựa trên hình ảnh như camera giám sát trong nhà [11, 18], hoặc điện thoại thông minh [12, 15, 19], cùng nhiều loại khác.

Bài báo này trình bày CareFall, một FDS tự động dựa trên các thiết bị đeo và các phương pháp Trí tuệ Nhân tạo (AI). Hình 1 cung cấp một mô tả đồ họa về CareFall. CareFall xem xét kịch bản trong đó đồng hồ thông minh được đeo trên cổ tay, thu thập thông tin liên quan đến các cảm biến quán tính của nó, chẳng hạn như gia tốc kế 3 trục và con quay hồi chuyển [8, 9], hoặc máy đo nhịp tim [13, 14]. Sau khi thông tin được thu thập bởi đồng hồ thông minh, các tín hiệu thời gian (tín hiệu gia tốc và con quay hồi chuyển) được sử dụng để trích xuất đặc trưng và phân loại. Hai phương pháp tiếp cận khác nhau được xem xét: i) dựa trên ngưỡng, và ii) dựa trên học máy. Trong trường hợp FDS phát hiện thấy một cú ngã, nó sẽ tự động cảnh báo cho các dịch vụ khẩn cấp.

---

## 2. PHƯƠNG PHÁP (METHODS)
CareFall xem xét hai trong số các phương pháp phổ biến nhất để phát hiện té ngã trong tài liệu nghiên cứu [23]. Chúng được cung cấp dữ liệu từ các tín hiệu thời gian 3 trục của cảm biến gia tốc kế và con quay hồi chuyển. Tần số lấy mẫu của đồng hồ thông minh là từ 20-25Hz. Để phân tích đơn giản và theo thời gian thực, chúng tôi xem xét các cửa sổ thời gian riêng biệt dài **1 phút**.

1.  **Dựa trên ngưỡng (Threshold-based):** Đây là một trong những giải pháp đơn giản nhất và ít tốn kém nhất về mặt tính toán để phát hiện té ngã. Nó dựa trên việc trích xuất các tín hiệu thời gian bổ sung từ các tín hiệu gia tốc và con quay hồi chuyển gốc như Vector Độ lớn Tín hiệu (SMV), Chỉ số Té ngã (FI) và Hướng dọc Tuyệt đối (AVD), cùng những chỉ số khác [4, 5]. Sau đó, một ngưỡng cụ thể được xác định cho mỗi chuỗi thời gian. Trong trường hợp giá trị tức thời của chuỗi thời gian vượt quá ngưỡng, đầu ra của hệ thống sẽ là "té ngã" (fall). Cần nhấn mạnh rằng, trong trường hợp xem xét đồng thời nhiều tín hiệu thời gian (ví dụ: SMV, FI và AVD), đầu ra cuối cùng của hệ thống sẽ dựa trên cơ chế biểu quyết đa số (majority voting) của tất cả các tín hiệu thời gian được xem xét.

2.  **Dựa trên Học máy (Machine Learning-based):** Cách tiếp cận này tự động học các mẫu phân biệt cho nhiệm vụ bằng cách sử dụng dữ liệu. Từ 6 tín hiệu thời gian gốc (gia tốc kế 3 trục và con quay hồi chuyển) và 2 tín hiệu thời gian bổ sung (SMV của gia tốc và con quay hồi chuyển), chúng tôi trích xuất **11 đặc trưng toàn cục** cho mỗi cửa sổ thời gian (1 phút) liên quan đến thông tin thống kê: Trung bình (Mean), Phương sai (Variance), Trung vị (Median), Delta, Độ lệch chuẩn (Standard Deviation), Giá trị cực đại (Maximum Value), Giá trị cực tiểu (Minimum Value), Bách phân vị thứ 25, Bách phân vị thứ 75, Mật độ phổ công suất (PSD) và Entropy phổ công suất (PSE). Tổng cộng, chúng tôi thu được một vectơ đặc trưng với 44 đặc trưng toàn cục liên quan đến thông tin gia tốc kế và 44 đặc trưng toàn cục liên quan đến con quay hồi chuyển. Sau khi có vectơ đặc trưng với 88 đặc trưng toàn cục, chúng tôi huấn luyện các bộ phân loại học máy cho nhiệm vụ phát hiện té ngã. Các thuật toán được sử dụng rộng rãi nhất là K-Hàng xóm gần nhất (KNN) [27], Máy vectơ hỗ trợ (SVM) [10], Gradient Boosting (GB) [26], Rừng ngẫu nhiên (Random Forest - RF) [26] và Mạng nơ-ron nhân tạo (ANN) [1], cùng những thuật toán khác.

---

## 3. THIẾT LẬP THỰC NGHIỆM (EXPERIMENTAL SETUP)
Hai cơ sở dữ liệu công khai phổ biến được xem xét trong khung thực nghiệm của bài báo: Erciyes University [27] và UMAFall [6]. Bảng 1 hiển thị thông tin liên quan nhất từ các cơ sở dữ liệu này: i) số lượng các Hoạt động Đời sống Hằng ngày (ADLs) như đi bộ, ngồi, nằm xuống, v.v., và các cú té ngã mô phỏng (ngã về phía trước, phía sau, sang bên, v.v.); ii) thông tin về người tham gia (số lượng, giới tính, chiều cao, cân nặng và độ tuổi); iii) loại tín hiệu thời gian thu được (gia tốc kế và con quay hồi chuyển); iv) vị trí cảm biến; và v) tần số lấy mẫu. Tiêu chí chính để lựa chọn các cơ sở dữ liệu này là vị trí của cảm biến (cổ tay), tần số lấy mẫu của cảm biến (20-25Hz) và tính đa dạng trong các loại hoạt động và té ngã.

Về quy trình thực nghiệm, cả hai cơ sở dữ liệu được chia thành tập dữ liệu phát triển (80% người tham gia) và tập dữ liệu đánh giá cuối cùng (20% người tham gia còn lại). Do đó, các đối tượng khác nhau được xem xét cho việc huấn luyện và đánh giá cuối cùng của CareFall. Về các chỉ số, chúng tôi xem xét ba chỉ số phổ biến trong tài liệu nghiên cứu: Độ nhạy (Sensitivity - SE), Độ đặc hiệu (Specificity - SP) và Độ chính xác (Accuracy). SE đề cập đến xác suất phát hiện một cú té ngã, SP là xác suất phát hiện một trường hợp không té ngã (tức là ADLs), và độ chính xác đề cập đến hiệu suất tổng thể của hệ thống.

---

## 4. KẾT QUẢ THỰC NGHIỆM (EXPERIMENTAL RESULTS)
Bảng 2 (phía trên) cho thấy kết quả của cơ sở dữ liệu Erciyes University trên tập đánh giá cuối cùng. Các kết quả được trình bày tương ứng với cấu hình tốt nhất của mỗi phương pháp phát hiện té ngã. Các kết quả thu được nói chung (độ chính xác) với phương pháp dựa trên ngưỡng kém hơn đáng kể so với phương pháp học máy (77.3% so với 98.4%), dẫn đến số lượng kết quả dương tính giả cao hơn (các trường hợp không té ngã bị phát hiện là té ngã). Xu hướng này có thể được quan sát bằng cách nhìn vào độ đặc hiệu (68.4% so với 96.7%). Tuy nhiên, điều thú vị cần lưu ý là phương pháp Ngưỡng vượt trội hơn phương pháp Học máy về độ nhạy (100% so với 98.9%), cho thấy đây là một cách tiếp cận đơn giản nhưng hiệu quả để phát hiện té ngã. Ngoài ra, khi phân tích phương pháp Học máy, chúng ta có thể thấy việc kết hợp thông tin gia tốc kế (44 đặc trưng toàn cục) và thông tin con quay hồi chuyển (44 đặc trưng toàn cục) đạt được kết quả tốt nhất.

Cuối cùng, chúng ta cũng có thể thấy ở Bảng 2 (phía dưới) kết quả đạt được cho cơ sở dữ liệu công khai UMAFall. Các kết luận tương tự cũng thu được, mặc dù kết quả tốt hơn đạt được trên cơ sở dữ liệu Erciyes. Điều này có thể do chất lượng của thiết bị và quá trình thu thập dữ liệu. Điều này cho thấy rằng việc kết hợp thông tin gia tốc kế và con quay hồi chuyển là một phương pháp tốt cho nhiệm vụ phát hiện té ngã.

---

## 5. LỜI CẢM ƠN (ACKNOWLEDGMENTS)
Công việc này được hỗ trợ bởi các dự án: INTER-ACTION (PID2021-126521OBI00 MICINN/FEDER), HumanCAIC (TED2021-131787BI00 MICINN), và Cartronic Group.

---

## TÀI LIỆU THAM KHẢO (REFERENCES)
1. Abbate, S., et al. (2012). A Smartphone-Based Fall Detection System. Pervasive and Mobile Computing.
2. Ambrose, A. F., et al. (2013). Risk Factors for Falls Among Older Adults: A Review of the Literature. Maturitas.
3. Bourke, A.K., et al. (2007). Evaluation of a Threshold-Based Tri-Axial Accelerometer Fall Detection Algorithm. Gait & Posture.
4. Casilari, E., & Oviedo-Jiménez, M. A. (2015). Automatic Fall Detection System Based on the Combined Use of a Smartphone and a Smartwatch. PLOS ONE.
5. Casilari, E., et al. (2017). Analysis of Public Datasets for Wearable Fall Detection Systems. Sensors.
6. Casilari, E., et al. (2017). UMAFall: A Multisensor Dataset for the Research on Automatic Fall Detection. Procedia Computer Science.
7. Delahoz, Y. S., & Labrador, M. A. (2014). Survey on Fall Detection and Fall Prevention Using Wearable and External Sensors. Sensors.
8. Delgado-Santos, P., et al. (2023). Exploring Transformers for Behavioural Biometrics: A Case Study in Gait Recognition. Pattern Recognition.
9. Delgado-Santos, P., et al. (2022). GaitPrivacyON: Privacy-Preserving Mobile Gait Biometrics using Unsupervised Learning. Pattern Recognition Letters.
10. Dinh, A., et al. (2009). Implementation of a Physical Activity Monitoring System for the Elderly People with Built-in Vital Sign and Fall Detection. ITNG.
11. Galvão, Y. M., et al. (2021). A Multimodal Approach Using Deep Learning for Fall Detection. Expert Systems with Applications.
12. Guvensan, M. A., et al. (2017). An Energy-Efficient Multi-Tier Architecture for Fall Detection on Smartphones. Sensors.
13. Hernandez-Ortega, J., et al. (2020). Heart Rate Estimation from Face Videos for Student Assessment: Experiments on edBB. COMPSAC.
14. Hernandez-Ortega, J., et al. (2021). DeepFakesON-Phys: DeepFakes Detection based on Heart Rate Estimation. AAAIw.
15. Kau, L-J., & Chen, C-S. (2015). A Smart Phone-Based Pocket Fall Accident Detection, Positioning, and Rescue System. JBHI.
16. Kwolek, B., & Kepski, M. (2014). Human Fall Detection on Embedded Platform Using Depth Maps and Wireless Accelerometer. CBMP.
17. Martínez-Villaseñor, L., et al. (2019). UP-Fall Detection Dataset: A Multimodal Approach. Sensors.
18. Mastorakis, G., et al. (2018). Fall Detection Without People: A Simulation Approach Tackling Video Data Scarcity. Expert Systems with Applications.
19. Mellone, S., et al. (2012). Smartphone-Based Solutions for Fall Detection and Prevention: the FARSEEING Approach. ZGG.
20. WHO (2017). Falls.
21. Rashidi, P., & Mihailidis, A. (2013). A Survey on Ambient-Assisted Living Tools for Older Adults. JBHI.
22. Romero-Tapiador, S., et al. (2023). AI4FoodDB: A Database for Personalized e-Health Nutrition and Lifestyle through Wearable Devices and AI. Database.
23. Schwickert, L., et al. (2013). Fall Detection with Body-Worn Sensors. ZGG.
24. Sucerquia, A., et al. (2017). SisFall: A Fall and Movement Dataset. Sensors.
25. Zhang, Z., et al. (2015). A Survey on Vision-Based Fall Detection. PETRA.
26. Zurbuchen, N., et al. (2021). A Machine Learning Multi-Class Approach for Fall Detection Systems Based on Wearable Sensors with a Study on Sampling Rates Selection. Sensors.
27. Özdemir, A. T., & Barshan, B. (2014). Detecting Falls with Wearable Sensors Using Machine Learning Techniques. Sensors.
